"""
Defines the abstract base class (interface) for vector store operations,
including insertion, search, and ID retrieval by text.
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any

class VectorStore(ABC):
    @abstractmethod
    async def insert_vectors(self, data: List[Dict[str, Any]]) -> List[Any]:
        """Insert vectors with metadata into the vector store and return their IDs."""
        pass

    @abstractmethod
    async def search_vectors(
        self, query_embeddings: List[List[float]], top_k: int = 5, similarity_threshold: float = 0.75
    ) -> List[Dict[str, Any]]:
        """Search vectors in the store and return relevant metadata."""
        pass

    @abstractmethod
    async def get_vector_id_by_text(self, text: str) -> Any:
        """Retrieve vector ID for an exact text match, or None if not found."""
        pass 