from typing import List, Dict, Any

from ..prompts import info_extraction_system_prompt, keyword_extraction_system_prompt
from .extractor import InfoExtractor, KeywordExtractor
from .models import ExtractedInfoList, ExtractedKeywordList
from ..clients.openai_client import OpenAIClient
from pydantic import BaseModel
import logging
from pydantic import ValidationError

logger = logging.getLogger(__name__)

"""OpenAI-based extractor implementations module.

Provides classes for personal information and keyword extraction using the OpenAI Responses API.
"""

class OpenAIInfoExtractor(InfoExtractor):
    """Extractor that identifies personal information from user messages via OpenAI."""
    def __init__(self, client: OpenAIClient = None):
        """Initialize with an OpenAI client instance."""
        self.client = client or OpenAIClient()

    async def extract(self, user_message: str) -> ExtractedInfoList:
        """
        Send a prompt to OpenAI to extract personal information.

        Args:
            user_message (str): The input message from the user.

        Returns:
            ExtractedInfoList: Parsed personal information items, empty list on error.
        """
        messages = [
            {"role": "system", "content": info_extraction_system_prompt},
            {"role": "user", "content": user_message},
        ]
        try:
            return await self.client.ask(input_list=messages, output_format=ExtractedInfoList)
        except ValidationError as e:
            logger.error(f"JSON parsing failed in OpenAIInfoExtractor: {e}", exc_info=True)
            return ExtractedInfoList(information=[])

class OpenAIKeywordExtractor(KeywordExtractor):
    """Extractor that identifies keywords from user messages via OpenAI."""
    def __init__(self, client: OpenAIClient = None):
        """Initialize with an OpenAI client instance."""
        self.client = client or OpenAIClient()

    async def extract(self, user_message: str) -> Dict[str, Any]:
        """
        Send a prompt to OpenAI to extract keywords.

        Args:
            user_message (str): The input message from the user.

        Returns:
            ExtractedKeywordList: Parsed list of keywords.
        """
        messages = [
            {"role": "system", "content": keyword_extraction_system_prompt},
            {"role": "user", "content": user_message},
        ]
        return await self.client.ask(input_list=messages, output_format=ExtractedKeywordList)