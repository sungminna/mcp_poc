from typing import List
from pydantic import BaseModel, Field
from typing import Optional

class ExtractedInfo(BaseModel):
    username: Optional[str] = Field(None, description="Username associated with this information")
    key: str = Field(..., description="Category hypernym of the value")
    value: str = Field(..., description="Specific noun or adjective")
    relationship: str = Field(..., description="Verb describing user's connection")
    lifetime: str = Field(..., description="Duration: 'permanent', 'long', 'short', or ISO datetime")

class ExtractedInfoList(BaseModel):
    information: List[ExtractedInfo] 

class ExtractedKeywordList(BaseModel):
    keywords: List[str]
