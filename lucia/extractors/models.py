"""Extractor models module.

Defines Pydantic schemas for personal information extraction and keyword lists.
"""
from typing import List
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class ExtractedInfo(BaseModel):
    """
    Schema for a single extracted personal information item.

    Attributes:
        username (Optional[str]): Associated user identifier.
        key (str): Hypernym category of the value.
        value (str): Extracted noun or adjective.
        relationship (str): Verb describing the user's relation to the value.
        lifetime (str): Duration ('permanent', 'long', 'short') or ISO datetime string.
    """
    username: Optional[str] = Field(None, description="Username associated with this information")
    key: str = Field(..., description="Category hypernym of the value")
    value: str = Field(..., description="Specific noun or adjective")
    relationship: str = Field(..., description="Verb describing user's connection")
    lifetime: str = Field(..., description="Duration: 'permanent', 'long', 'short', or ISO datetime")
    # inserted_at: Optional[str] = Field(None, description="Timestamp when this information was inserted (ISO 8601 string)")

class ExtractedInfoDB(BaseModel):
    """
    Extended schema for database storage of extracted information.

    Attributes:
        username (Optional[str]): Associated user identifier.
        key (str): Hypernym category of the value.
        value (str): Extracted noun or adjective.
        relationship (str): Verb describing the user's relation to the value.
        lifetime (str): Duration or ISO datetime string.
        inserted_at (Optional[str]): ISO timestamp when the record was saved.
    """
    username: Optional[str] = Field(None, description="Username associated with this information")
    key: str = Field(..., description="Category hypernym of the value")
    value: str = Field(..., description="Specific noun or adjective")
    relationship: str = Field(..., description="Verb describing user's connection")
    lifetime: str = Field(..., description="Duration: 'permanent', 'long', 'short', or ISO datetime")
    inserted_at: Optional[str] = Field(None, description="Timestamp when this information was inserted (ISO 8601 string)")

class ExtractedInfoList(BaseModel):
    """
    Container for a list of ExtractedInfo items returned by extractors.

    Attributes:
        information (List[ExtractedInfo]): Extracted personal info items.
    """
    information: List[ExtractedInfo] 

class ExtractedInfoDBList(BaseModel):
    """
    Container for a list of ExtractedInfoDB items used in database operations.

    Attributes:
        information (List[ExtractedInfoDB]): Info records with insertion timestamps.
    """
    information: List[ExtractedInfoDB]

class ExtractedKeywordList(BaseModel):
    """
    Container for keywords extracted from user messages.

    Attributes:
        keywords (List[str]): List of extracted keyword strings.
    """
    keywords: List[str]
