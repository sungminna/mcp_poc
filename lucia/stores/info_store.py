from abc import ABC, abstractmethod
from typing import List, Dict, Any

class InfoStore(ABC):
    @abstractmethod
    async def save_personal_information(self, username: str, info_list: List[Dict[str, Any]]):
        """Save personal information items for a user."""
        pass

    @abstractmethod
    async def find_similar_information(
        self, username: str, keywords: List[str], top_k: int = 3, similarity_threshold: float = 0.75
    ) -> List[str]:
        """Retrieve list of related information strings based on keywords."""
        pass 