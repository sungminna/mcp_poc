from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.orm import relationship # If relationships are needed later

from database import Base
from pydantic import BaseModel, EmailStr
from typing import Optional

# SQLAlchemy model (represents the 'users' table)
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)

# Pydantic model for request data (password required)
class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str

# Pydantic model for response data (password excluded)
class UserResponse(BaseModel):
    id: int
    username: str
    email: EmailStr
    is_active: bool

    class Config:
        from_attributes = True

# Pydantic model for token data
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None 