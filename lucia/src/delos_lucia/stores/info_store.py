"""InfoStore interface module.

Defines the abstract contract for persistent storage of extracted personal information.
Implementations must support saving and querying user-specific ExtractedInfo entries.
"""
from abc import ABC, abstractmethod
from typing import List
from ..extractors.models import ExtractedInfo

class InfoStore(ABC):
    """Abstract interface for storage backends handling personal information data."""
    @abstractmethod
    async def save_personal_information(self, username: str, info_list: List[ExtractedInfo]):
        """
        Persist personal information items for a specified user.

        Args:
            username (str): Unique identifier of the user.
            info_list (List[ExtractedInfo]): List of ExtractedInfo objects to store.
        """
        pass

    @abstractmethod
    async def find_similar_information(
        self, username: str, keywords: List[str], top_k: int = 3, similarity_threshold: float = 0.75
    ) -> List[ExtractedInfo]:
        """
        Retrieve personal information entries matching given keywords.

        Args:
            username (str): Unique identifier of the user.
            keywords (List[str]): Keywords to match against stored information.
            top_k (int): Maximum number of results to return.
            similarity_threshold (float): Minimum similarity score for matches.

        Returns:
            List[ExtractedInfo]: List of matching ExtractedInfo objects.
        """
        pass 