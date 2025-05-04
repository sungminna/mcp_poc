"""MilvusVectorStore module.

Implements a singleton vector store backend using Milvus for embedding insertion,
similarity search, and vector ID retrieval, with background flushing support.
"""
from typing import List, Dict, Any, Optional
from .vector_store import VectorStore
import asyncio
from ..config import settings
from pymilvus import (
    connections, utility, Collection, CollectionSchema, FieldSchema, DataType, Index
)
from pymilvus.exceptions import MilvusException
import logging
import threading
from queue import Queue
import atexit

logger = logging.getLogger(__name__)

MILVUS_COLLECTION_NAME = "knowledge_vectors"
MILVUS_VECTOR_FIELD = "embedding"
MILVUS_ELEMENT_TYPE_FIELD = "element_type"
MILVUS_TEXT_FIELD = "original_text"
EMBEDDING_DIMENSION = 1536
MILVUS_INDEX_NAME = "vector_hnsw_index"
VECTOR_INDEX_PARAMS = {
    "metric_type": "COSINE",
    "index_type": "HNSW",
    "params": {"M": 16, "efConstruction": 200}
}

class MilvusVectorStore(VectorStore):
    """Singleton Milvus-based VectorStore implementation.

    Manages a Milvus collection for storing and retrieving vector embeddings.
    Supports asynchronous insertion, search, and ID lookup operations.
    """
    _instance = None
    _initialized = False

    def __new__(cls, *args, **kwargs):
        """Implement singleton construction for the vector store instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """
        Initialize Milvus connection, collection schema, and background flush worker.

        Connects to Milvus, ensures the collection and index exist,
        and starts a daemon thread for background flushing.
        """
        if type(self)._initialized:
            return
        type(self)._initialized = True
        # Initialize host, port, alias, collection only once
        self._host = settings.milvus_host
        self._port = settings.milvus_port
        self._alias = "default"
        self._collection: Optional[Collection] = None
        # perform synchronous connection and prepare the collection/index
        try:
            connections.connect(alias=self._alias, host=self._host, port=self._port)
            self._ensure_collection_and_index()
        except Exception as e:
            raise RuntimeError(f"Failed to connect or prepare Milvus: {e}")
        # Start background flush worker
        self._flush_queue = Queue()
        t = threading.Thread(target=self._flush_worker, daemon=True)
        t.start()
        # Ensure pending flushes complete on process exit
        atexit.register(self._shutdown)

    def _ensure_collection_and_index(self):
        """
        Ensure the Milvus collection and HNSW index are created and loaded.

        Called during initialization to prepare the storage schema.
        """
        if not utility.has_collection(MILVUS_COLLECTION_NAME, using=self._alias):
            schema = CollectionSchema([
                FieldSchema(name=MILVUS_TEXT_FIELD, dtype=DataType.VARCHAR, max_length=5000, is_primary=True, auto_id=False),
                FieldSchema(name=MILVUS_VECTOR_FIELD, dtype=DataType.FLOAT_VECTOR, dim=EMBEDDING_DIMENSION),
                FieldSchema(name=MILVUS_ELEMENT_TYPE_FIELD, dtype=DataType.VARCHAR, max_length=32)
            ], description="Knowledge Vectors: Text Embeddings Only")
            self._collection = Collection(name=MILVUS_COLLECTION_NAME, schema=schema, using=self._alias)
            Index(self._collection, MILVUS_VECTOR_FIELD, VECTOR_INDEX_PARAMS, index_name=MILVUS_INDEX_NAME)
            self._collection.load()
        else:
            self._collection = Collection(name=MILVUS_COLLECTION_NAME, using=self._alias)
            if not self._collection.has_index():
                Index(self._collection, MILVUS_VECTOR_FIELD, VECTOR_INDEX_PARAMS, index_name=MILVUS_INDEX_NAME)
            if utility.load_state(MILVUS_COLLECTION_NAME) != "loaded":
                self._collection.load()

    def _flush_worker(self):
        """
        Background thread that listens for flush signals and commits data.

        Waits on a queue signal and calls Milvus collection.flush().
        """
        while True:
            # Wait for a flush signal
            self._flush_queue.get()
            try:
                self._collection.flush()
            except Exception as e:
                logger.error(f"[MilvusVectorStore worker] background flush failed: {e}", exc_info=True)
            finally:
                self._flush_queue.task_done()

    def _shutdown(self):
        """
        Shutdown handler to flush pending operations before process exit.

        Blocks until all queued flush tasks complete.
        """
        logger.info("[MilvusVectorStore] waiting for pending flush tasks to complete...")
        self._flush_queue.join()
        logger.info("[MilvusVectorStore] all pending flush tasks completed.")

    async def insert_vectors(self, data: List[Dict[str, Any]]) -> List[Any]:
        """
        Insert vector embeddings into Milvus and schedule a background flush.

        Args:
            data (List[Dict[str, Any]]): List of records with keys:
                'original_text', 'embedding', 'element_type'.

        Returns:
            List[Any]: Primary keys assigned by Milvus for inserted vectors.
        """
        if not data:
            return []
        # Prepare insertion payload with normalized text
        prepared_data = [
            {
                MILVUS_VECTOR_FIELD: item["embedding"],
                MILVUS_ELEMENT_TYPE_FIELD: item["element_type"],
                MILVUS_TEXT_FIELD: item["original_text"].lower()
            }
            for item in data
        ]
        try:
            result = await asyncio.to_thread(self._collection.insert, prepared_data)
            # Notify flush worker
            self._flush_queue.put(True)
            return result.primary_keys
        except Exception as e:
            raise RuntimeError(f"Failed to insert vectors: {e}")

    async def search_vectors(self, query_embeddings: List[List[float]], top_k: int = 5, similarity_threshold: float = 0.75) -> List[Dict[str, Any]]:
        """
        Perform similarity search on embeddings in the Milvus collection.

        Args:
            query_embeddings (List[List[float]]): Embedding vectors to search.
            top_k (int): Maximum number of results to return.
            similarity_threshold (float): Minimum score threshold for hits.

        Returns:
            List[Dict[str, Any]]: Top-k matching records with keys:
                'original_text', 'element_type', 'score'.
        """
        if not query_embeddings:
            return []
        search_params = {
            "data": query_embeddings,
            "anns_field": MILVUS_VECTOR_FIELD,
            "param": {"metric_type": "COSINE", "params": {"ef": 128}},
            "limit": top_k * 5,
            "output_fields": [MILVUS_TEXT_FIELD, MILVUS_ELEMENT_TYPE_FIELD]
        }
        try:
            results = await asyncio.to_thread(self._collection.search, **search_params)
            processed_hits = []
            seen = set()
            for hits in results:
                for hit in hits:
                    if hit.score >= similarity_threshold:
                        text = hit.entity.get(MILVUS_TEXT_FIELD)
                        etype = hit.entity.get(MILVUS_ELEMENT_TYPE_FIELD)
                        if text and text not in seen:
                            processed_hits.append({
                                "original_text": text,
                                "element_type": etype,
                                "score": hit.score
                            })
                            seen.add(text)
            processed_hits.sort(key=lambda x: x["score"], reverse=True)
            return processed_hits[:top_k]
        except Exception as e:
            raise RuntimeError(f"Failed to search vectors: {e}")

    async def get_vector_id_by_text(self, text: str) -> Optional[Any]:
        """
        Retrieve the Milvus primary key for an exact original text match.

        Args:
            text (str): The original text to lookup.

        Returns:
            Optional[Any]: Matching primary key if found, otherwise None.
        """
        normalized = text.strip().lower() if text else ""
        if not normalized:
            return None
        # Construct filter expression for exact match
        expr = f'{MILVUS_TEXT_FIELD} == "{normalized.replace("\"", "\\\"")}"'
        params = {
            "data": [],
            "anns_field": MILVUS_VECTOR_FIELD,
            "param": {},
            "limit": 1,
            "expr": expr,
            "output_fields": [MILVUS_TEXT_FIELD]
        }
        try:
            results = await asyncio.to_thread(self._collection.search, **params)
            if results and results[0]:
                return results[0][0].entity.get(MILVUS_TEXT_FIELD)
            return None
        except Exception:
            return None 