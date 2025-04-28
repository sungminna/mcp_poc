from typing import List, Dict, Any

from ..prompts import info_extraction_system_prompt, keyword_extraction_system_prompt
from .extractor import InfoExtractor, KeywordExtractor
from .models import ExtractedInfoList, ExtractedKeywordList
from ..clients.openai_client import OpenAIClient
from pydantic import BaseModel

class OpenAIInfoExtractor(InfoExtractor):
    """Extract personal information using OpenAI Responses API and JSON parser."""
    def __init__(self, client: OpenAIClient = None):
        self.client = client or OpenAIClient()

    async def extract(self, user_message: str) -> Dict[str, Any]:
        messages = [
            {"role": "system", "content": info_extraction_system_prompt},
            {"role": "user", "content": user_message},
        ]
        # Call the LLM and get raw JSON string
        json = await self.client.ask(input_list=messages, output_format=ExtractedInfoList)

        return json

class OpenAIKeywordExtractor(KeywordExtractor):
    """Extract keywords using OpenAI Responses API."""
    def __init__(self, client: OpenAIClient = None):
        self.client = client or OpenAIClient()

    async def extract(self, user_message: str) -> Dict[str, Any]:
        system = keyword_extraction_system_prompt
        messages = [
            {"role": "system", "content": keyword_extraction_system_prompt},
            {"role": "user", "content": user_message},
        ]
        json = await self.client.ask(input_list=messages, output_format=ExtractedKeywordList)
        
        return json