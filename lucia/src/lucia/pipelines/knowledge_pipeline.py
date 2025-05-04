from typing import Any, Dict, List
import logging

from ..extractors.extractor import KeywordExtractor, InfoExtractor
from ..extractors.noop_extractor import NoOpKeywordExtractor, NoOpInfoExtractor
from ..embeddings.embedding_client import EmbeddingClient
from ..vectorstores.vector_store import VectorStore
from ..stores.info_store import InfoStore

logger = logging.getLogger(__name__)

"""KnowledgePipeline module.

Implements an end-to-end pipeline for extracting personal information,
generating embeddings for keywords, and storing results in vector and graph databases.
"""

class KnowledgePipeline:
    """Pipeline for personal info extraction and keyword embedding storage."""

    def __init__(
        self,
        keyword_extractor: KeywordExtractor = None,
        embedding_client: EmbeddingClient = None,
        vector_store: VectorStore = None,
        info_extractor: InfoExtractor = None,
        info_store: InfoStore = None,
    ):
        """
        Initialize the pipeline with provided components or default no-op extractors.

        Args:
            keyword_extractor (KeywordExtractor, optional): Service for extracting keywords.
            embedding_client (EmbeddingClient, optional): Service for generating embeddings.
            vector_store (VectorStore, optional): Backend for vector storage.
            info_extractor (InfoExtractor, optional): Service for extracting personal info.
            info_store (InfoStore, optional): Backend for personal info storage.
        """
        # Use no-op extractors if none provided
        self.keyword_extractor = keyword_extractor or NoOpKeywordExtractor()
        self.embedding_client = embedding_client
        self.vector_store = vector_store
        self.info_extractor = info_extractor or NoOpInfoExtractor()
        self.info_store = info_store

    async def process(
        self,
        user_message: str,
        username: str,
    ) -> Dict[str, Any]:
        """
        Process a user's message through information and keyword pipelines.

        Steps:
            1. Extract and persist personal information.
            2. Extract keywords, embed them, and store embeddings.

        Args:
            user_message (str): User's input text.
            username (str): Identifier for the user's context.

        Returns:
            Dict[str, Any]: {
                'info_list': List of extracted personal info items,
                'vector_ids': List of IDs for inserted embeddings
            }
        """
        result: Dict[str, Any] = {}

        # Extract and persist personal information
        info_list: List[Dict[str, Any]] = []  # List of extracted personal info records
        try:
            info_result = await self.info_extractor.extract(user_message)
            info_list = info_result.information
            # Store extracted info in graph DB if present
            if info_list:
                # Save personal information synchronously before returning
                await self.info_store.save_personal_information(username, info_list)
                logger.info(f"Saved {len(info_list)} info items to graph DB.")
            result['info_list'] = info_list
        except Exception as e:
            logger.error(f"Info extraction or graph storage failed: {e}", exc_info=True)
            result['info_list'] = []

        # Embed extracted keywords and insert into vector store
        vector_ids: List[Any] = []
        try:
            # Build keyword list from extracted info
            keywords: List[str] = []
            for info in info_list:
                keywords.extend([info.key, info.value, info.relationship])
            if keywords:
                embeddings = await self.embedding_client.embed_text(keywords)
                # Prepare data for vector store
                data: List[Dict[str, Any]] = [
                    {"original_text": kw, "embedding": emb, "element_type": "keyword"}
                    for kw, emb in zip(keywords, embeddings)
                ]
                vector_ids = await self.vector_store.insert_vectors(data)
                result['vector_ids'] = vector_ids
                logger.info(f"Inserted {len(vector_ids)} keyword vectors into vector store.")
            else:
                result['vector_ids'] = []
        except Exception as e:
            logger.error(f"Embedding or vector insertion failed: {e}", exc_info=True)
            result['vector_ids'] = []

        return result 