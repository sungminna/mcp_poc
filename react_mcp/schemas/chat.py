from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class ChatRequest(BaseModel):
    session_id: Optional[int] = Field(None, description="ID of the chat session; if omitted, a new session will be created.")
    user_message: str

class ChatResponse(BaseModel):
    session_id: int
    question: str
    ai_response: str

    class Config:
        orm_mode = True

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