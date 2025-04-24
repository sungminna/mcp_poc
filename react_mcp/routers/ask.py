"""Chat router module: defines the /api/chat endpoints for interactive LLM-based chat with session management, rolling context, and user-specific context augmentation."""
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
import asyncio
import logging
from datetime import datetime
from collections import deque

from services.llm_service import llm_ask  # Core function to query the primary LLM-based REACT agent
from services.neo4j_service import neo4j_service  # Service for retrieving and storing user information in Neo4j
from models.user import User  # Pydantic model representing authenticated users
from core.security import get_current_active_user  # Dependency that returns the current active user
from database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from crud.chat import create_session, get_session, create_chat_message, get_sessions, get_messages, delete_session
from main import langfuse_handler, limiter, DEFAULT_CHAT_LIMIT, get_user_id_from_token  # Import Langfuse callback handler, limiter, and token-based key func

# Define the LLM model used for structured information and keyword extraction
from langchain_openai import ChatOpenAI  # LangChain client for OpenAI models
from langchain_core.output_parsers import JsonOutputParser  # Parser for extracting JSON-formatted LLM output
from .prompts import info_extraction_prompt, keyword_extraction_prompt
from typing import List, Optional

# Model instance for structured information and keyword extraction
extraction_model = ChatOpenAI(model="gpt-4.1-nano")  # LLM for info/keyword extraction

# In-memory store: session ID → deque of recent messages for building context
session_contexts: dict[int, deque] = {}
MAX_CONTEXT_MESSAGES = 10

# Pydantic models for representing extracted personal information
class ExtractedInfo(BaseModel):
    key: str = Field(description="The category or superset noun/adjective (e.g., 'Color', 'Food', 'Hobby')")
    value: str = Field(description="The specific noun/adjective (e.g., 'Blue', 'Pizza', 'Reading')")
    relationship: str = Field(description="The verb describing the user's connection (e.g., 'Likes', 'Dislikes', 'Is', 'Has', 'Prefers')")
    lifetime: str = Field(description="Estimated duration: 'permanent', 'long', 'short', or an ISO 8601 datetime string")

class ExtractedInfoList(BaseModel):
    information: List[ExtractedInfo] = Field(description="A list of extracted personal information snippets.")

# Chains for processing user messages

"""Extract personal information in structured JSON according to ExtractedInfoList schema."""
info_parser = JsonOutputParser(pydantic_object=ExtractedInfoList)
info_extraction_chain = info_extraction_prompt | extraction_model | info_parser

"""Identify comma-separated keywords for knowledge graph query."""
keyword_extraction_chain = keyword_extraction_prompt | extraction_model  # returns AIMessage content

# Define FastAPI router and endpoints for the chat interface

router = APIRouter()
logger = logging.getLogger(__name__)

class ChatRequest(BaseModel):
    session_id: Optional[int] = Field(None, description="ID of the chat session; if omitted, a new session will be created.")
    user_message: str

@router.post("/api/chat/", summary="Send a message to the LLM-based chat agent")
@limiter.limit(DEFAULT_CHAT_LIMIT, key_func=get_user_id_from_token)  # Use the configurable rate limit with token-based key func
async def ask(request: Request, request_data: ChatRequest, current_user: User = Depends(get_current_active_user), db: AsyncSession = Depends(get_db)):
    """Handle chat interaction: manage session, enrich context, query LLM, and persist results."""
    user_message = request_data.user_message
    username = current_user.username  # authenticated user's username

    logger.info(f"Processing chat request for user: {username}")

    # Session management: reuse or create session for this user
    if request_data.session_id:
        session = await get_session(db, request_data.session_id)
        if not session or session.user_id != current_user.id:
            raise HTTPException(status_code=404, detail="Chat session not found")
    else:
        session = await create_session(db, current_user.id)
    session_id = session.id

    # Initialize or load in-memory deque storing recent chat exchanges
    if session_id not in session_contexts:
        if request_data.session_id:
            past_messages = await get_messages(db, session_id)
            session_contexts[session_id] = deque(
                [(msg.sender, msg.content) for msg in past_messages[-MAX_CONTEXT_MESSAGES:]],
                maxlen=MAX_CONTEXT_MESSAGES
            )
        else:
            session_contexts[session_id] = deque(maxlen=MAX_CONTEXT_MESSAGES)

    # Store the user's message in the database
    await create_chat_message(db, session_id, "human", user_message)
    # Add the user's message to the context deque
    session_contexts[session_id].append(("human", user_message))

    # Context augmentation: extract keywords and fetch related info
    augmentation_context = ""
    try:
        # Extract keywords from the user's message
        keyword_result = await keyword_extraction_chain.ainvoke({"user_message": user_message}, config={"callbacks": [langfuse_handler]})
        keywords_str = keyword_result.content
        keywords = [kw.strip() for kw in keywords_str.split(',') if kw.strip()]
        logger.info(f"Extracted keywords for user '{username}': {keywords}")

        if keywords:
            # Fetch related user information from Neo4j for prompt enrichment
            similar_info_sentences = await neo4j_service.find_similar_information(username=username, keywords=keywords)

            if similar_info_sentences:
                # Format retrieved relationships as bullet points for inclusion
                augmentation_context = "\n\nRelevant background information about the user:\n- " + "\n- ".join(similar_info_sentences)
                logger.info(f"Augmenting prompt for user '{username}' with context:'{augmentation_context[:100]}...'")
            else:
                 logger.info(f"No similar information found in Neo4j for user '{username}'.")

    except Exception as e:
        logger.error(f"Error during keyword extraction or similarity search for user '{username}': {e}", exc_info=True)
        # Continue without augmentation if this phase fails

    # Build the prompt combining history, current message, and augmentation; then invoke LLM
    history_text = ""
    if session_contexts[session_id]:
        # Format conversation history from the context deque
        history_text = "Conversation History:\n" + "\n".join([
            f"{'User' if sender=='human' else 'AI'}: {content}"
            for sender, content in session_contexts[session_id]
        ])
    # Construct the full prompt: History (if any), new user message, and augmentation context
    prompt_input = (history_text + "\n\n" if history_text else "") + f"User: {user_message}" + augmentation_context
    logger.debug(f"Augmented prompt for user '{username}': \n{prompt_input}")

    try:
        # Query the primary LLM-based REACT agent
        res = await llm_ask(prompt_input)

        if res and 'response' in res:
            try:
                # Extract the final AI response from the agent's output
                final_message = res['response'].get('output') # Adjust based on actual output structure
                if not final_message and isinstance(res['response'], dict) and 'messages' in res['response']:
                     # Fallback if output isn't directly available (older LangGraph versions?)
                     final_message = res['response']['messages'][-1].content

                if final_message:
                    logger.info(f"Successfully generated final response for user '{username}' in session {session_id}")
                    # Save the AI response and update the context deque
                    await create_chat_message(db, session_id, "agent", final_message)
                    # Update rolling context with new agent message
                    session_contexts[session_id].append(("agent", final_message))

                    # Asynchronously extract personal information from the user message
                    try:
                        # Parse structured info using the extraction chain
                        extraction_result = await info_extraction_chain.ainvoke({
                            "user_message": user_message,
                            "format_instructions": info_parser.get_format_instructions()
                        }, config={"callbacks": [langfuse_handler]})
                        extracted_info_list = extraction_result.get('information', [])

                        if extracted_info_list:
                            logger.info(f"Extracted {len(extracted_info_list)} info items for user '{username}' (background). Saving to Neo4j.")
                            # Schedule background task to persist extracted info to Neo4j
                            asyncio.create_task(
                                neo4j_service.save_personal_information(username=username, info_list=extracted_info_list)
                            )
                            # Note: scheduling does not block response delivery
                        else:
                            logger.info(f"No personal information extracted for user '{username}' (background).")

                    except Exception as e:
                        logger.error(f"Error during background information extraction or scheduling save for user '{username}': {e}", exc_info=True)
                        # Do not block response return if background task fails

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

# Endpoints to list, retrieve, and delete chat sessions and associated messages

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
async def list_sessions(request: Request, current_user: User = Depends(get_current_active_user), db: AsyncSession = Depends(get_db)):
    """List all chat sessions for the current user with first question and answer preview"""
    db_sessions = await get_sessions(db, current_user.id)
    sessions = []
    for sess in db_sessions:
        msgs = await get_messages(db, sess.id)
        # Get first human query and first AI response
        first_user = msgs[0].content if len(msgs) > 0 else ""
        first_ai = msgs[1].content if len(msgs) > 1 else ""
        sessions.append({"id": sess.id, "first_user_message": first_user, "first_ai_response": first_ai})
    return sessions

@router.get("/api/chat/{session_id}/messages", response_model=List[MessageResponse], tags=["chat"])
async def list_messages(request: Request, session_id: int, current_user: User = Depends(get_current_active_user), db: AsyncSession = Depends(get_db)):
    """Retrieve all messages for a given chat session"""
    session = await get_session(db, session_id)
    if not session or session.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Chat session not found")
    messages = await get_messages(db, session_id)
    return messages

@router.delete("/api/chat/{session_id}", status_code=204, tags=["chat"])
async def remove_session(request: Request, session_id: int, current_user: User = Depends(get_current_active_user), db: AsyncSession = Depends(get_db)):
    """Delete a chat session and its messages"""
    session = await get_session(db, session_id)
    if not session or session.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Chat session not found")
    await delete_session(db, session_id)
    # Clear rolling context cache for deleted session
    if session_id in session_contexts:
        del session_contexts[session_id]
    return 