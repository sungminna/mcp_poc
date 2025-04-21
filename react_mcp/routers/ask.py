from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
import asyncio
import logging
from datetime import datetime
from collections import deque

from services.llm_service import llm_ask # The main REACT agent call
from services.neo4j_service import neo4j_service
from models.user import User # Assuming you have a User model for dependency
from core.security import get_current_active_user # Function to get authenticated user
from database import get_db
from sqlalchemy.orm import Session
from crud.chat import create_session, get_session, create_chat_message, get_sessions, get_messages, delete_session
from main import langfuse_handler  # Import Langfuse callback handler

# TODO: Import or define the LLM model instance used for extraction/keyword generation
# from services.llm_service import model as extraction_model # Example if using the same model
# Or use a dedicated model/client for these tasks
from langchain_openai import ChatOpenAI # Placeholder
from langchain_core.output_parsers import JsonOutputParser # For structured output
from .prompts import info_extraction_prompt, keyword_extraction_prompt
from typing import List, Optional

# Placeholder: Define LLM for extraction/keywords if not using the main one
# Make sure API keys are loaded via load_dotenv() in main.py or llm_service.py
extraction_model = ChatOpenAI(model="gpt-4.1-nano") # Use a suitable model

router = APIRouter()
logger = logging.getLogger(__name__)

# In-memory rolling context for each chat session
session_contexts: dict[int, deque] = {}
MAX_CONTEXT_MESSAGES = 10

# --- Pydantic models for LLM extraction ---
class ExtractedInfo(BaseModel):
    key: str = Field(description="The category or superset noun/adjective (e.g., 'Color', 'Food', 'Hobby')")
    value: str = Field(description="The specific noun/adjective (e.g., 'Blue', 'Pizza', 'Reading')")
    relationship: str = Field(description="The verb describing the user's connection (e.g., 'Likes', 'Dislikes', 'Is', 'Has', 'Prefers')")
    lifetime: str = Field(description="Estimated duration: 'permanent', 'long', 'short', or an ISO 8601 datetime string")

class ExtractedInfoList(BaseModel):
    information: List[ExtractedInfo] = Field(description="A list of extracted personal information snippets.")

# --- LLM Chains (using LangChain Expression Language - LCEL) ---

# 1. Information Extraction Chain
info_parser = JsonOutputParser(pydantic_object=ExtractedInfoList)
info_extraction_chain = info_extraction_prompt | extraction_model | info_parser

# 2. Keyword Extraction Chain
keyword_extraction_chain = keyword_extraction_prompt | extraction_model # Output is AIMessage, get content

# --- Router Definition ---

class ChatRequest(BaseModel):
    session_id: Optional[int] = Field(None, description="ID of the chat session; if omitted, a new session will be created.")
    user_message: str

@router.post("/api/chat/")
async def ask(request: ChatRequest, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    user_message = request.user_message
    username = current_user.username # Get username from authenticated user

    logger.info(f"Processing chat request for user: {username}")

    # Handle chat session creation or retrieval
    if request.session_id:
        session = get_session(db, request.session_id)
        if not session or session.user_id != current_user.id:
            raise HTTPException(status_code=404, detail="Chat session not found")
    else:
        session = create_session(db, current_user.id)
    session_id = session.id

    # Initialize or load rolling context window
    if session_id not in session_contexts:
        if request.session_id:
            past_messages = get_messages(db, session_id)
            session_contexts[session_id] = deque(
                [(msg.sender, msg.content) for msg in past_messages[-MAX_CONTEXT_MESSAGES:]],
                maxlen=MAX_CONTEXT_MESSAGES
            )
        else:
            session_contexts[session_id] = deque(maxlen=MAX_CONTEXT_MESSAGES)

    # Save user's message to the database
    create_chat_message(db, session_id, "human", user_message)
    # Update rolling context with new user message
    session_contexts[session_id].append(("human", user_message))

    # --- Step 3 & 4: Extract Info & Save (Run in Background) ---
    extracted_info_list = []
    try:
        # Call LLM to extract information
        extraction_result = await info_extraction_chain.ainvoke({
            "user_message": user_message,
            "format_instructions": info_parser.get_format_instructions()
        }, config={"callbacks": [langfuse_handler]})
        extracted_info_list = extraction_result.get('information', [])

        if extracted_info_list:
            logger.info(f"Extracted {len(extracted_info_list)} info items for user '{username}'. Saving to Neo4j.")
            # The parser already returns a list of dicts
            # Directly pass the list of dictionaries
            # await asyncio.create_task( # Don't run in background, await completion
            await neo4j_service.save_personal_information(username=username, info_list=extracted_info_list)
            # )
            logger.info(f"Finished saving information for user '{username}'.") # Add log after saving
        else:
            logger.info(f"No personal information extracted for user '{username}'.")

    except Exception as e:
        logger.error(f"Error during information extraction or saving for user '{username}': {e}", exc_info=True)
        # Continue processing the chat request even if extraction/saving fails

    # --- Step 5, 6, 7: Extract Keywords, Search Neo4j, Summarize --- 
    augmentation_context = ""
    try:
        # 5. Extract Keywords
        keyword_result = await keyword_extraction_chain.ainvoke({"user_message": user_message}, config={"callbacks": [langfuse_handler]})
        keywords_str = keyword_result.content
        keywords = [kw.strip() for kw in keywords_str.split(',') if kw.strip()]
        logger.info(f"Extracted keywords for user '{username}': {keywords}")

        if keywords:
            # 6. Search Neo4j (Method needs implementation + vector index)
            # This method should return a list of strings, each describing a relevant relationship.
            similar_info_sentences = await neo4j_service.find_similar_information(username=username, keywords=keywords)

            if similar_info_sentences:
                # 7. Summarize / Format for Prompt
                augmentation_context = "\n\nRelevant background information about the user:\n- " + "\n- ".join(similar_info_sentences)
                logger.info(f"Augmenting prompt for user '{username}' with context:'{augmentation_context[:100]}...'")
            else:
                 logger.info(f"No similar information found in Neo4j for user '{username}'.")

    except Exception as e:
        logger.error(f"Error during keyword extraction or similarity search for user '{username}': {e}", exc_info=True)
        # Continue without augmentation if this phase fails

    # --- Step 8 & 9: Build rolling context, augment prompt, and call main LLM ---
    # Build conversation history prompt from rolling context
    history_text = ""
    if session_contexts[session_id]:
        history_text = "\n".join([
            f"{'User' if sender=='human' else 'AI'}: {content}"
            for sender, content in session_contexts[session_id]
        ])
    prompt_input = (history_text + "\n" if history_text else "") + user_message + augmentation_context
    logger.debug(f"Augmented prompt for user '{username}': \n{prompt_input}")

    try:
        # Call the main REACT agent with the potentially augmented question
        res = await llm_ask(prompt_input)

        if res and 'response' in res:
            try:
                # Ensure the response structure is handled correctly
                # The structure depends on what `create_react_agent(...).ainvoke` returns
                # It often includes intermediate steps. We usually want the final message.
                final_message = res['response'].get('output') # Adjust based on actual output structure
                if not final_message and isinstance(res['response'], dict) and 'messages' in res['response']:
                     # Fallback if output isn't directly available (older LangGraph versions?)
                     final_message = res['response']['messages'][-1].content

                if final_message:
                    logger.info(f"Successfully generated final response for user '{username}' in session {session_id}")
                    # Save AI's response to the database
                    create_chat_message(db, session_id, "agent", final_message)
                    # Update rolling context with new agent message
                    session_contexts[session_id].append(("agent", final_message))
                    return {"session_id": session_id, "question": user_message, "ai_response": final_message}
                else:
                    logger.error(f"Could not extract final message content from LLM response for user '{username}'. Response: {res['response']}")
                    return {"session_id": session_id, "question": user_message, "ai_response": "Error processing LLM response structure."}                    

            except Exception as e:
                logger.error(f"Error extracting content from LLM response for user '{username}': {e}. Response: {res['response']}", exc_info=True)
                return {"session_id": session_id, "question": user_message, "ai_response": "Error processing LLM response content."} 

        elif res and 'error' in res:
            logger.error(f"LLM Error for user '{username}': {res['error']}")
            return {"session_id": session_id, "question": user_message, "ai_response": f"LLM Error: {res['error']}"} 
        else:
            logger.error(f"Unknown LLM response structure for user '{username}': {res}")
            return {"session_id": session_id, "question": user_message, "ai_response": "Unknown error from LLM service."} 
            
    except Exception as e:
        logger.error(f"Error calling main LLM agent for user '{username}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error generating AI response") 

# --- Chat session management endpoints ---

class SessionResponse(BaseModel):
    id: int
    first_user_message: str = Field(..., description="Content of the first human query in the session")
    first_ai_response: str = Field(..., description="Content of the first AI response in the session")

    class Config:
        orm_mode = True

class MessageResponse(BaseModel):
    id: int
    session_id: int
    sender: str
    content: str
    created_at: datetime

    class Config:
        orm_mode = True

@router.get("/api/chat/sessions", response_model=List[SessionResponse], tags=["chat"])
async def list_sessions(current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    """List all chat sessions for the current user with first question and answer preview"""
    db_sessions = get_sessions(db, current_user.id)
    sessions = []
    for sess in db_sessions:
        msgs = get_messages(db, sess.id)
        # Get first human query and first AI response
        first_user = msgs[0].content if len(msgs) > 0 else ""
        first_ai = msgs[1].content if len(msgs) > 1 else ""
        sessions.append({"id": sess.id, "first_user_message": first_user, "first_ai_response": first_ai})
    return sessions

@router.get("/api/chat/{session_id}/messages", response_model=List[MessageResponse], tags=["chat"])
async def list_messages(session_id: int, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    """Retrieve all messages for a given chat session"""
    session = get_session(db, session_id)
    if not session or session.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Chat session not found")
    messages = get_messages(db, session_id)
    return messages

@router.delete("/api/chat/{session_id}", status_code=204, tags=["chat"])
async def remove_session(session_id: int, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    """Delete a chat session and its messages"""
    session = get_session(db, session_id)
    if not session or session.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Chat session not found")
    delete_session(db, session_id)
    # Clear rolling context cache for deleted session
    if session_id in session_contexts:
        del session_contexts[session_id]
    return 