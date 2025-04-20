from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
import asyncio
import logging

from services.llm_service import llm_ask # The main REACT agent call
from services.neo4j_service import neo4j_service
from models.user import User # Assuming you have a User model for dependency
from core.security import get_current_active_user # Function to get authenticated user

# TODO: Import or define the LLM model instance used for extraction/keyword generation
# from services.llm_service import model as extraction_model # Example if using the same model
# Or use a dedicated model/client for these tasks
from langchain_openai import ChatOpenAI # Placeholder
from langchain_core.output_parsers import JsonOutputParser # For structured output
from .prompts import info_extraction_prompt, keyword_extraction_prompt
from typing import List

# Placeholder: Define LLM for extraction/keywords if not using the main one
# Make sure API keys are loaded via load_dotenv() in main.py or llm_service.py
extraction_model = ChatOpenAI(model="gpt-4.1-nano") # Use a suitable model

router = APIRouter()
logger = logging.getLogger(__name__)

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
    user_message: str

@router.post("/api/chat/")
async def ask(request: ChatRequest, current_user: User = Depends(get_current_active_user)):
    user_message = request.user_message
    username = current_user.username # Get username from authenticated user

    logger.info(f"Processing chat request for user: {username}")

    # --- Step 3 & 4: Extract Info & Save (Run in Background) ---
    extracted_info_list = []
    print("aasdfasdf")
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

    # --- Step 8 & 9: Augment Prompt & Call Main LLM --- 
    augmented_question = user_message + augmentation_context
    logger.debug(f"Augmented question for user '{username}': \n{augmented_question}")

    try:
        # Call the main REACT agent with the potentially augmented question
        res = await llm_ask(augmented_question)

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
                    logger.info(f"Successfully generated final response for user '{username}'")
                    return {"question": user_message, "ai_response": final_message}
                else:
                    logger.error(f"Could not extract final message content from LLM response for user '{username}'. Response: {res['response']}")
                    return {"question": user_message, "ai_response": "Error processing LLM response structure."}                    

            except Exception as e:
                logger.error(f"Error extracting content from LLM response for user '{username}': {e}. Response: {res['response']}", exc_info=True)
                return {"question": user_message, "ai_response": "Error processing LLM response content."} 

        elif res and 'error' in res:
            logger.error(f"LLM Error for user '{username}': {res['error']}")
            return {"question": user_message, "ai_response": f"LLM Error: {res['error']}"} 
        else:
            logger.error(f"Unknown LLM response structure for user '{username}': {res}")
            return {"question": user_message, "ai_response": "Unknown error from LLM service."} 
            
    except Exception as e:
        logger.error(f"Error calling main LLM agent for user '{username}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error generating AI response") 