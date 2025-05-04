from typing import List, Dict, Any

from ..prompts import info_extraction_system_prompt, keyword_extraction_system_prompt
from .extractor import InfoExtractor, KeywordExtractor
from .models import ExtractedInfoList, ExtractedKeywordList
from ..clients.openai_client import OpenAIClient
from pydantic import BaseModel
import logging
from pydantic import ValidationError

logger = logging.getLogger(__name__)

"""
Module for OpenAI-based extractors for personal information and keywords.
"""

class OpenAIInfoExtractor(InfoExtractor):
    """Extract personal information using OpenAI Responses API and JSON parser."""
    def __init__(self, client: OpenAIClient = None):
        self.client = client or OpenAIClient()

    async def extract(self, user_message: str) -> ExtractedInfoList:
        messages = [
            {"role": "system", "content": info_extraction_system_prompt},
            {"role": "user", "content": user_message},
        ]
        try:
            info_list_model = await self.client.ask(input_list=messages, output_format=ExtractedInfoList)
            return info_list_model
        except ValidationError as e:
            logger.error(f"OpenAIInfoExtractor: JSON parsing failed: {e}", exc_info=True)
            # Return an empty information list on parse failure
            return ExtractedInfoList(information=[])

class OpenAIKeywordExtractor(KeywordExtractor):
    """Extract keywords using OpenAI Responses API."""
    def __init__(self, client: OpenAIClient = None):
        self.client = client or OpenAIClient()

    async def extract(self, user_message: str) -> Dict[str, Any]:
        """Send prompt to OpenAI for keyword extraction and parse response into ExtractedKeywordList."""
        system = keyword_extraction_system_prompt
        messages = [
            {"role": "system", "content": keyword_extraction_system_prompt},
            {"role": "user", "content": user_message},
        ]
        json = await self.client.ask(input_list=messages, output_format=ExtractedKeywordList)
        
        return json