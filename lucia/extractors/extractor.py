from abc import ABC, abstractmethod
from typing import List, Dict, Any

class InfoExtractor(ABC):
    @abstractmethod
    async def extract(self, user_message: str) -> Dict[str, Any]:
        """Extract personal information items from user message."""
        pass

class KeywordExtractor(ABC):
    @abstractmethod
    async def extract(self, user_message: str) -> Dict[str, Any]:
        """Extract keywords from user message."""
        pass 