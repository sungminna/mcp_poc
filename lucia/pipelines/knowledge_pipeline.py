from typing import Any, Dict, List
import logging

from ..extractors.extractor import KeywordExtractor, InfoExtractor
from ..extractors.noop_extractor import NoOpKeywordExtractor, NoOpInfoExtractor
from ..embeddings.embedding_client import EmbeddingClient
from ..vectorstores.vector_store import VectorStore
from ..stores.info_store import InfoStore

logger = logging.getLogger(__name__)

class KnowledgePipeline:
    """
    Pipeline for extracting keywords, embedding them into a vector DB,
    and extracting personal info relations to store in a graph DB.
    """
    def __init__(
        self,
        keyword_extractor: KeywordExtractor = None,
        embedding_client: EmbeddingClient = None,
        vector_store: VectorStore = None,
        info_extractor: InfoExtractor = None,
        info_store: InfoStore = None,
    ):
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
        Process a user message through the pipeline:
        1) Extract keywords
        2) Embed keywords and store in vector DB
        3) Extract personal info relationships and store in graph DB

        Returns a dict with keys: 'keywords', 'vector_ids', 'info_list', 'relationships'.
        """
        result: Dict[str, Any] = {}

        # 1. Keyword extraction
        try:
            keywords_result = await self.keyword_extractor.extract(user_message)
            keywords = keywords_result.keywords
            result['keywords'] = keywords
            logger.info(f"Extracted keywords: {keywords}")
        except Exception as e:
            logger.error(f"Keyword extraction failed: {e}", exc_info=True)
            keywords = []
            result['keywords'] = []
        # 2. Embedding and vector store insertion
        vector_ids: List[Any] = []
        if keywords:
            try:
                embeddings = await self.embedding_client.embed_text(keywords)
                # Prepare data for vector store
                data: List[Dict[str, Any]] = []
                for kw, emb in zip(keywords, embeddings):
                    data.append({
                        "original_text": kw,
                        "embedding": emb,
                        "element_type": "keyword"
                    })
                vector_ids = await self.vector_store.insert_vectors(data)
                result['vector_ids'] = vector_ids
                logger.info(f"Inserted {len(vector_ids)} keyword vectors into vector store.")
            except Exception as e:
                logger.error(f"Embedding or vector insertion failed: {e}", exc_info=True)
                result['vector_ids'] = []
        else:
            result['vector_ids'] = []

        # 3. Personal info extraction and graph storage
        info_list: List[Dict[str, Any]] = []
        try:
            info_result = await self.info_extractor.extract(user_message)
            info_list = info_result.information
            if info_list:
                # Save personal information synchronously before returning
                await self.info_store.save_personal_information(username, info_list)
                logger.info(f"Saved {len(info_list)} info items to graph DB.")
        except Exception as e:
            logger.error(f"Info extraction or graph storage failed: {e}", exc_info=True)
            result['info_list'] = []

        return result 