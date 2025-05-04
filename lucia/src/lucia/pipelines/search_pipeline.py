"""SearchPipeline module.

Implements a pipeline to extract keywords, perform vector similarity searches,
and retrieve user-specific information from the info store.
"""

from typing import Any, Dict, List
import logging

from ..extractors.extractor import KeywordExtractor, InfoExtractor
from ..extractors.noop_extractor import NoOpKeywordExtractor, NoOpInfoExtractor
from ..embeddings.embedding_client import EmbeddingClient
from ..vectorstores.vector_store import VectorStore
from ..stores.info_store import InfoStore

logger = logging.getLogger(__name__)

class SearchPipeline:
    """Pipeline for keyword extraction, vector search, and personal info retrieval."""

    def __init__(
        self,
        keyword_extractor: KeywordExtractor = None,
        embedding_client: EmbeddingClient = None,
        vector_store: VectorStore = None,
        info_extractor: InfoExtractor = None,
        info_store: InfoStore = None,
    ):
        """Initialize the search pipeline with provided components or default no-op extractors.

        Args:
            keyword_extractor (KeywordExtractor, optional): Service to extract keywords.
            embedding_client (EmbeddingClient): Service to generate embeddings.
            vector_store (VectorStore): Backend for vector operations.
            info_extractor (InfoExtractor, optional): Service to extract personal info.
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
        """Run the search pipeline on a user message.

        Steps:
            1. Extract keywords.
            2. Embed keywords and perform vector similarity search.
            3. Retrieve matching personal info entries.

        Args:
            user_message (str): The user's input text.
            username (str): Identifier for the user context.

        Returns:
            Dict[str, Any]: {
                'keywords': List[str],
                'vector_ids': List[Any],
                'info_list': List[ExtractedInfo],
                'relationships': List[str]
            }
        """
        result: Dict[str, Any] = {}

        # Step 1: Extract keywords
        try:
            keywords_result = await self.keyword_extractor.extract(user_message)
            keywords = keywords_result.keywords
            result['keywords'] = keywords
        except Exception as e:
            logger.error(f"Keyword extraction failed: {e}", exc_info=True)
            keywords = []
            result['keywords'] = []

        # Step 2: Embed keywords and perform vector similarity search
        vector_ids: List[Any] = []
        if keywords:
            try:
                embeddings = await self.embedding_client.embed_text(keywords)
                # Retrieve similar vectors from the vector store
                similar_hits = await self.vector_store.search_vectors(embeddings, top_k=5)
                # Append similar texts to the keyword list
                similar_keywords = [hit['original_text'] for hit in similar_hits]
                keywords.extend(similar_keywords)
                result['keywords'] = keywords
                result['vector_ids'] = []  # skipping insertion in this mode
            except Exception as e:
                logger.error(f"Embedding or search failed: {e}", exc_info=True)
                result['vector_ids'] = []
        else:
            result['vector_ids'] = []

        # Step 3: Retrieve personal information matching keywords
        info_list: List[Dict[str, Any]] = []
        try:
            if keywords and self.info_store:
                # Fetch matching records from the info store
                info_list = await self.info_store.find_similar_information(username, keywords)
                result['info_list'] = info_list
                # Construct human-readable relationship descriptions
                result['relationships'] = [
                    f"I(User) {rec.relationship} {rec.value} (a {rec.key}) for {rec.lifetime}, info inserted at {rec.inserted_at}." for rec in info_list
                ]
            else:
                result['info_list'] = []
                result['relationships'] = []
        except Exception as e:
            logger.error(f"Info search failed: {e}", exc_info=True)
            result['info_list'] = []
            result['relationships'] = []

        return result 