"""
Defines the abstract base class (interface) for text embedding clients.
"""
from abc import ABC, abstractmethod
from typing import List

class EmbeddingClient(ABC):
    @abstractmethod
    async def embed_text(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for the given list of texts."""
        pass 