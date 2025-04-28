from typing import List, Dict, Any
from .extractor import InfoExtractor, KeywordExtractor

class NoOpInfoExtractor(InfoExtractor):
    async def extract(self, user_message: str) -> List[Dict[str, Any]]:
        """No-op extractor that returns an empty list."""
        return []

class NoOpKeywordExtractor(KeywordExtractor):
    async def extract(self, user_message: str) -> List[str]:
        """No-op keyword extractor that returns an empty list."""
        return [] 