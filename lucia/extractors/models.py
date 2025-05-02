from typing import List
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class ExtractedInfo(BaseModel):
    username: Optional[str] = Field(None, description="Username associated with this information")
    key: str = Field(..., description="Category hypernym of the value")
    value: str = Field(..., description="Specific noun or adjective")
    relationship: str = Field(..., description="Verb describing user's connection")
    lifetime: str = Field(..., description="Duration: 'permanent', 'long', 'short', or ISO datetime")
    # inserted_at: Optional[str] = Field(None, description="Timestamp when this information was inserted (ISO 8601 string)")

class ExtractedInfoDB(BaseModel):
    username: Optional[str] = Field(None, description="Username associated with this information")
    key: str = Field(..., description="Category hypernym of the value")
    value: str = Field(..., description="Specific noun or adjective")
    relationship: str = Field(..., description="Verb describing user's connection")
    lifetime: str = Field(..., description="Duration: 'permanent', 'long', 'short', or ISO datetime")
    inserted_at: Optional[str] = Field(None, description="Timestamp when this information was inserted (ISO 8601 string)")

class ExtractedInfoList(BaseModel):
    information: List[ExtractedInfo] 

class ExtractedInfoDBList(BaseModel):
    information: List[ExtractedInfoDB]

class ExtractedKeywordList(BaseModel):
    keywords: List[str]
