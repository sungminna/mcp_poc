"""Extractor interface module.

Defines abstract base classes for personal information and keyword extraction.
"""
from abc import ABC, abstractmethod
from typing import List
from .models import ExtractedInfoList, ExtractedKeywordList

class InfoExtractor(ABC):
    @abstractmethod
    async def extract(self, user_message: str) -> ExtractedInfoList:
        """Extract personal information items from user message and return an ExtractedInfoList."""
        pass

class KeywordExtractor(ABC):
    @abstractmethod
    async def extract(self, user_message: str) -> ExtractedKeywordList:
        """Extract keywords from user message and return an ExtractedKeywordList."""
        pass 