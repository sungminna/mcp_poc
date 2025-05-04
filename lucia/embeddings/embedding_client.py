"""
EmbeddingClient interface module.

Defines an abstract base class for text embedding services.
Implementations must provide a method to generate vector embeddings for batches of text inputs.
"""
from abc import ABC, abstractmethod
from typing import List

class EmbeddingClient(ABC):
    """
    Abstract base class for embedding client implementations.

    Provides a contract for generating vector embeddings from text.
    """
    @abstractmethod
    async def embed_text(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple text inputs.

        Args:
            texts (List[str]): List of text strings to embed.

        Returns:
            List[List[float]]: List of embedding vectors corresponding to each text.
        """
        pass 