from typing import List
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class ExtractedInfo(BaseModel):
    """
    Pydantic model representing a single piece of extracted personal information.
    Fields:
      - username: Optional user identifier
      - key: Superordinate category of the value
      - value: Extracted noun or adjective
      - relationship: Verb describing how the user relates to the value
      - lifetime: Duration for which the relation holds
    """
    username: Optional[str] = Field(None, description="Username associated with this information")
    key: str = Field(..., description="Category hypernym of the value")
    value: str = Field(..., description="Specific noun or adjective")
    relationship: str = Field(..., description="Verb describing user's connection")
    lifetime: str = Field(..., description="Duration: 'permanent', 'long', 'short', or ISO datetime")
    # inserted_at: Optional[str] = Field(None, description="Timestamp when this information was inserted (ISO 8601 string)")

class ExtractedInfoDB(BaseModel):
    """
    Extended Pydantic model for database storage of extracted information.
    Includes timestamp when the record was inserted.
    """
    username: Optional[str] = Field(None, description="Username associated with this information")
    key: str = Field(..., description="Category hypernym of the value")
    value: str = Field(..., description="Specific noun or adjective")
    relationship: str = Field(..., description="Verb describing user's connection")
    lifetime: str = Field(..., description="Duration: 'permanent', 'long', 'short', or ISO datetime")
    inserted_at: Optional[str] = Field(None, description="Timestamp when this information was inserted (ISO 8601 string)")

class ExtractedInfoList(BaseModel):
    """
    Container model for a list of ExtractedInfo objects returned by extractors.
    """
    information: List[ExtractedInfo] 

class ExtractedInfoDBList(BaseModel):
    """
    Container model for a list of ExtractedInfoDB objects used for DB operations.
    """
    information: List[ExtractedInfoDB]

class ExtractedKeywordList(BaseModel):
    """
    Container model for a list of keywords extracted from user input.
    """
    keywords: List[str]
