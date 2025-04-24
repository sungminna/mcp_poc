"""Chat router module: defines the /api/chat endpoints for interactive LLM-based chat with session management, rolling context, and user-specific context augmentation."""
from fastapi import APIRouter, Depends, HTTPException
from starlette.requests import Request
from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional

from services.chat_service import handle_conversation, session_contexts
from models.user import User
from core.depends import limiter, get_user_id_from_token, get_current_active_user, get_db
from sqlalchemy.ext.asyncio import AsyncSession
from crud.chat import get_sessions, get_messages, get_session, delete_session
from core.config import RATE_LIMIT_CHAT

# Define FastAPI router and endpoints for the chat interface

router = APIRouter()

class ChatRequest(BaseModel):
    session_id: Optional[int] = Field(None, description="ID of the chat session; if omitted, a new session will be created.")
    user_message: str

class ChatResponse(BaseModel):
    session_id: int
    question: str
    ai_response: str

    class Config:
        orm_mode = True

@router.post(
    "/",
    summary="Send a message to the LLM-based chat agent",
    response_model=ChatResponse,
    tags=["chat"],
)
@limiter.limit(RATE_LIMIT_CHAT, key_func=get_user_id_from_token)
async def ask(
    request: Request,
    request_data: ChatRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> ChatResponse:
    """Handle chat interaction by delegating to chat_service."""
    session_id, ai_response = await handle_conversation(
        user_message=request_data.user_message,
        session_id=request_data.session_id,
        user_id=current_user.id,
        username=current_user.username,
        db=db,
    )
    return {"session_id": session_id, "question": request_data.user_message, "ai_response": ai_response}

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

@router.get("/sessions", response_model=List[SessionResponse], tags=["chat"])
async def list_sessions(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> List[SessionResponse]:
    """List all chat sessions for the current user with first question and answer preview"""
    db_sessions = await get_sessions(db, current_user.id)
    sessions = []
    for sess in db_sessions:
        msgs = await get_messages(db, sess.id)
        first_user = msgs[0].content if len(msgs) > 0 else ""
        first_ai = msgs[1].content if len(msgs) > 1 else ""
        sessions.append({"id": sess.id, "first_user_message": first_user, "first_ai_response": first_ai})
    return sessions

@router.get("/{session_id}/messages", response_model=List[MessageResponse], tags=["chat"])
async def list_messages(
    session_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> List[MessageResponse]:
    """Retrieve all messages for a given chat session"""
    session = await get_session(db, session_id)
    if not session or session.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Chat session not found")
    messages = await get_messages(db, session_id)
    return messages

@router.delete("/{session_id}", status_code=204, tags=["chat"])
async def remove_session(
    session_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> None:
    """Delete a chat session and its messages"""
    session = await get_session(db, session_id)
    if not session or session.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Chat session not found")
    await delete_session(db, session_id)
    if session_id in session_contexts:
        del session_contexts[session_id]
    return 