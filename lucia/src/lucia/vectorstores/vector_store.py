"""
VectorStore interface module.

Defines the contract for vector database backends, supporting insertion,
nearest-neighbor search, and retrieval of vector IDs by original text.
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any

class VectorStore(ABC):
    """
    Abstract interface for vector store clients.

    Implementations must support inserting embeddings with metadata,
    executing similarity searches, and fetching vector IDs by text.
    """
    @abstractmethod
    async def insert_vectors(self, data: List[Dict[str, Any]]) -> List[Any]:
        """
        Insert vector embeddings along with metadata into the store.

        Args:
            data (List[Dict[str, Any]]): List of dicts each containing:
                - 'original_text' (str): Source text.
                - 'embedding' (List[float]): Corresponding vector.
                - 'element_type' (str): Label for the embedding.

        Returns:
            List[Any]: IDs assigned to the inserted vectors.
        """
        pass

    @abstractmethod
    async def search_vectors(
        self, query_embeddings: List[List[float]], top_k: int = 5, similarity_threshold: float = 0.75
    ) -> List[Dict[str, Any]]:
        """
        Find similar vectors for given query embeddings.

        Args:
            query_embeddings (List[List[float]]): Embeddings to query.
            top_k (int): Maximum number of results to return.
            similarity_threshold (float): Minimum similarity score to include.

        Returns:
            List[Dict[str, Any]]: List of metadata for matching vectors,
                containing 'original_text', 'element_type', and 'score'.
        """
        pass

    @abstractmethod
    async def get_vector_id_by_text(self, text: str) -> Any:
        """
        Retrieve the vector ID associated with an exact text match.

        Args:
            text (str): Original text to look up.

        Returns:
            Any: Matching vector ID, or None if no match is found.
        """
        pass 