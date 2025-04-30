from abc import ABC, abstractmethod
from typing import List
from ..extractors.models import ExtractedInfo

class InfoStore(ABC):
    @abstractmethod
    async def save_personal_information(self, username: str, info_list: List[ExtractedInfo]):
        """Save personal information items for a user using ExtractedInfo models."""
        pass

    @abstractmethod
    async def find_similar_information(
        self, username: str, keywords: List[str], top_k: int = 3, similarity_threshold: float = 0.75
    ) -> List[ExtractedInfo]:
        """Retrieve personal information items matching keywords as ExtractedInfo models."""
        pass 