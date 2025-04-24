import logging
import asyncio
from collections import deque
from typing import Optional, Tuple, List

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from crud.chat import create_session, get_session, create_chat_message, get_messages
from services.llm_service import llm_ask
from services.neo4j_service import neo4j_service
from core.depends import langfuse_handler

# Prompt templates and chains
from routers.prompts import info_extraction_prompt, keyword_extraction_prompt
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field

# In-memory context store: session ID → deque of messages
session_contexts: dict[int, deque] = {}
MAX_CONTEXT_MESSAGES = 10
logger = logging.getLogger(__name__)

# Pydantic models for structured info extraction
class ExtractedInfo(BaseModel):
    key: str = Field(description="Category hypernym of the value")
    value: str = Field(description="Specific noun/adjective")
    relationship: str = Field(description="Verb describing user's connection")
    lifetime: str = Field(description="Duration: 'permanent', 'long', 'short', or ISO 8601 datetime")

class ExtractedInfoList(BaseModel):
    information: List[ExtractedInfo]

# Chains for processing messages
extraction_model = ChatOpenAI(model="gpt-4.1-nano")
info_parser = JsonOutputParser(pydantic_object=ExtractedInfoList)
info_extraction_chain = info_extraction_prompt | extraction_model | info_parser
keyword_extraction_chain = keyword_extraction_prompt | extraction_model

async def handle_conversation(
    user_message: str,
    session_id: Optional[int],
    user_id: int,
    username: str,
    db: AsyncSession
) -> Tuple[int, str]:
    """
    Handle chat session: create/retrieve session, enrich context, call LLM, persist messages, and schedule background info extraction.
    Returns (session_id, ai_response).
    """
    # Session management
    if session_id:
        session = await get_session(db, session_id)
        if not session or session.user_id != user_id:
            raise HTTPException(status_code=404, detail="Chat session not found")
    else:
        session = await create_session(db, user_id)
    session_id = session.id

    # Load or initialize conversation history
    if session_id not in session_contexts:
        past = await get_messages(db, session_id)
        session_contexts[session_id] = deque(
            [(msg.sender, msg.content) for msg in past[-MAX_CONTEXT_MESSAGES:]],
            maxlen=MAX_CONTEXT_MESSAGES
        )

    # Persist user message
    await create_chat_message(db, session_id, "human", user_message)
    session_contexts[session_id].append(("human", user_message))

    # Context augmentation: extract keywords and fetch related info
    augmentation_context = ""
    try:
        keyword_result = await keyword_extraction_chain.ainvoke(
            {"user_message": user_message}, config={"callbacks": [langfuse_handler]}
        )
        keywords_str = keyword_result.content
        keywords = [k.strip() for k in keywords_str.split(",") if k.strip()]
        logger.info(f"Extracted keywords for user '{username}': {keywords}")
        if keywords:
            similar = await neo4j_service.find_similar_information(username=username, keywords=keywords)
            if similar:
                augmentation_context = (
                    "\n\nRelevant background information about the user:\n- " +
                    "\n- ".join(similar)
                )
                logger.info(f"Augmented prompt context: {augmentation_context[:100]}...")
    except Exception as e:
        logger.error(f"Keyword extraction or similarity search failed: {e}", exc_info=True)

    # Build prompt
    history = session_contexts[session_id]
    history_text = "Conversation History:\n" + "\n".join([
        f"{'User' if s=='human' else 'AI'}: {c}" for s, c in history
    ]) if history else ""
    prompt = (history_text + "\n\n" if history_text else "") + f"User: {user_message}" + augmentation_context

    # Call the LLM agent
    try:
        res = await llm_ask(prompt)
    except Exception as e:
        logger.error(f"Error calling LLM agent: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error generating AI response")

    # Parse the response
    final_message = None
    if res and 'response' in res:
        resp = res['response']
        final_message = resp.get('output')
        if not final_message and isinstance(resp, dict) and 'messages' in resp:
            final_message = resp['messages'][-1].content
    if not final_message:
        logger.error(f"Invalid LLM response structure: {res}")
        raise HTTPException(status_code=500, detail="Error processing LLM response")

    # Persist AI response
    await create_chat_message(db, session_id, "agent", final_message)
    session_contexts[session_id].append(("agent", final_message))

    # Background personal info extraction and save to Neo4j
    try:
        extraction_result = await info_extraction_chain.ainvoke(
            {"user_message": user_message, "format_instructions": info_parser.get_format_instructions()},
            config={"callbacks": [langfuse_handler]}
        )
        info_list = extraction_result.get("information", [])
        if info_list:
            logger.info(f"Extracted {len(info_list)} info items; saving to Neo4j.")
            asyncio.create_task(
                neo4j_service.save_personal_information(username=username, info_list=info_list)
            )
    except Exception as e:
        logger.error(f"Personal info extraction failed: {e}", exc_info=True)

    return session_id, final_message 