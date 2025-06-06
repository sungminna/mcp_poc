"""Milvus service module: manages connection to a Milvus vector store, ensures collection and index setup, and provides vector insert/search operations for embedding-based queries."""

import os
import logging
import asyncio
import json # Added for JSON handling
from pymilvus import (
    connections,
    utility,
    Collection,
    CollectionSchema,
    FieldSchema,
    DataType,
    Index,
)
from pymilvus.exceptions import MilvusException, CollectionNotExistException, IndexNotExistException
from dotenv import load_dotenv
from typing import List, Dict, Any, Tuple, Optional

load_dotenv() # Load environment variables from .env file

logger = logging.getLogger(__name__)

# --- Milvus Configuration ---
MILVUS_COLLECTION_NAME = "knowledge_vectors"
MILVUS_ID_FIELD = "milvus_id" # Primary key
MILVUS_VECTOR_FIELD = "embedding"
MILVUS_ELEMENT_TYPE_FIELD = "element_type" # 'Node', 'Relationship', 'CategoryNode'
MILVUS_TEXT_FIELD = "original_text"

# Keep OpenAI Embedding Config here for reference or move to a central config
OPENAI_EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSION = 1536

VECTOR_INDEX_PARAMS = {
    "metric_type": "COSINE", # Use COSINE similarity
    "index_type": "HNSW", # Using HNSW index
    "params": {"M": 16, "efConstruction": 200} # Index parameters, tune as needed
}
MILVUS_INDEX_NAME = "vector_hnsw_index"


# --- Sync Helper Functions for Milvus (thread-safe operations) ---

def _sync_create_collection(alias: str, schema: CollectionSchema):
    """Create a Milvus collection with the specified schema in a separate thread."""
    try:
        collection = Collection(name=MILVUS_COLLECTION_NAME, schema=schema, using=alias)
        logger.info(f"Milvus collection '{MILVUS_COLLECTION_NAME}' created successfully.")
        return collection
    except MilvusException as e:
        logger.error(f"Failed to create Milvus collection '{MILVUS_COLLECTION_NAME}': {e}", exc_info=True)
        raise

def _sync_create_index(collection: Collection, field_name: str):
    """Build a vector index on the specified field for the given Milvus collection."""
    try:
        index = Index(collection, field_name, VECTOR_INDEX_PARAMS, index_name=MILVUS_INDEX_NAME)
        logger.info(f"Creating Milvus index '{MILVUS_INDEX_NAME}' on field '{field_name}'. This may take time...")
        logger.info(f"Milvus index '{MILVUS_INDEX_NAME}' creation initiated.")
        return index
    except MilvusException as e:
        logger.error(f"Failed to create Milvus index '{MILVUS_INDEX_NAME}' on field '{field_name}': {e}", exc_info=True)
        raise

def _sync_insert_vectors(collection: Collection, data: List[Dict[str, Any]]) -> List[Any]:
    """Insert multiple vectors with metadata into Milvus, returning generated IDs."""
    try:
        logger.debug(f"Inserting {len(data)} vectors into Milvus collection '{MILVUS_COLLECTION_NAME}'...")
        mutation_result = collection.insert(data)
        inserted_ids = mutation_result.primary_keys
        logger.info(f"Successfully inserted {len(inserted_ids)} vectors. Example ID: {inserted_ids[0] if inserted_ids else 'N/A'}")
        collection.flush()  # Ensure persistence
        logger.debug("Milvus collection flushed after insertion.")
        return inserted_ids
    except MilvusException as e:
        logger.error(f"Failed to insert vectors into Milvus: {e}", exc_info=True)
        raise

def _sync_search_vectors(collection: Collection, search_vectors: List[List[float]], top_k: int, similarity_threshold: float) -> List[Dict[str, Any]]:
    """Perform a cosine similarity search for given vectors, filtering by threshold and returning top hits."""
    search_params = {
        "data": search_vectors,
        "anns_field": MILVUS_VECTOR_FIELD,
        "param": {"metric_type": "COSINE", "params": {"ef": 128}},
        "limit": top_k * 5,
        # Note: Filtering by element type can be applied in search if needed
        "output_fields": [MILVUS_TEXT_FIELD, MILVUS_ELEMENT_TYPE_FIELD]
    }
    try:
        # Ensure the collection is loaded for efficient search
        if not collection.has_index():
            logger.warning(f"Collection '{MILVUS_COLLECTION_NAME}' has no index; search performance may suffer.")
        is_loaded = utility.load_state(MILVUS_COLLECTION_NAME) == "loaded"
        if not is_loaded:
            logger.info(f"Loading Milvus collection '{MILVUS_COLLECTION_NAME}' for search...")
            collection.load()
            utility.wait_for_loading_complete(MILVUS_COLLECTION_NAME)
            logger.info(f"Milvus collection '{MILVUS_COLLECTION_NAME}' loaded.")

        results = collection.search(**search_params)
        logger.debug(f"Milvus search returned {len(results)} hit groups.")

        processed_hits = []
        # Results is a list of lists (one list per query vector)
        unique_texts = set() # Track unique texts to avoid duplicates if searching across multiple query vectors
        for hits in results:
            for hit in hits:
                # Apply similarity threshold filter
                if hit.score >= similarity_threshold:
                    original_text = hit.entity.get(MILVUS_TEXT_FIELD)
                    element_type = hit.entity.get(MILVUS_ELEMENT_TYPE_FIELD)
                    if original_text and original_text not in unique_texts:
                        processed_hits.append({
                            "original_text": original_text,
                            "element_type": element_type,
                            "score": hit.score
                        })
                        unique_texts.add(original_text)
                    # else: skip duplicate text or hit without text

        # Sort by score descending (Milvus results are usually sorted, but good to ensure)
        processed_hits.sort(key=lambda x: x["score"], reverse=True)
        # Deduplication logic removed as it was based on Neo4j ID
        # Now returning unique texts found across all query vectors, sorted by score

        logger.info(f"Milvus search yielded {len(processed_hits)} unique text hits above threshold {similarity_threshold}.")
        # Return the top_k results after deduplication
        return processed_hits[:top_k]

    except MilvusException as e:
        logger.error(f"Milvus search error: {e}", exc_info=True)
        return []
    except Exception as e:
        logger.error(f"Unexpected error during Milvus search: {e}", exc_info=True)
        return []

def _sync_get_vector_id_by_text(collection: Collection, text: str) -> Optional[int]:
    """Retrieve Milvus vector ID for an exact original_text match, or None if not found."""
    normalized_text = text.strip().lower()
    if not normalized_text:
        logger.warning("Attempted to search Milvus by empty/whitespace text.")
        return None

    escaped_text = normalized_text.replace('"', '\"')
    expr = f'{MILVUS_TEXT_FIELD} == "{escaped_text}"'
    search_params = {
        "data": [], 
        "anns_field": MILVUS_VECTOR_FIELD, 
        "param": {}, 
        "limit": 1,
        "expr": expr,
        "output_fields": [MILVUS_TEXT_FIELD] 
    }
    logger.debug(f"Executing Milvus text search with expr: {expr}") # Log expression
    try:
        results = collection.search(**search_params)
        logger.debug(f"Raw Milvus text search result for '{normalized_text[:50]}...': {results}") # Log raw result
        
        if results and results[0]:
            first_hit = results[0][0]
            original_text = first_hit.entity.get(MILVUS_TEXT_FIELD)
            if original_text:
                logger.info(f"Found existing Milvus vector for text: '{original_text[:50]}...'") # Changed level to INFO
                return original_text
            else:
                logger.info(f"No existing Milvus vector found for text: '{normalized_text[:50]}...'") # Changed level to INFO
                return None
        else:
            logger.info(f"No existing Milvus vector found for text: '{normalized_text[:50]}...'") # Changed level to INFO
            return None
    except MilvusException as e:
        logger.error(f"Milvus error searching by text '{normalized_text[:50]}...': {e}", exc_info=True)
        return None
    except Exception as e:
        logger.error(f"Unexpected error searching Milvus by text '{normalized_text[:50]}...': {e}", exc_info=True)
        return None

# --- MilvusService Class ---
### Core class: MilvusService - vector store lifecycle and operations
class MilvusService:
    """Manages Milvus connection, collection/index setup, and provides vector insert/search APIs."""
    def __init__(self):
        self._host = os.getenv("MILVUS_HOST", "localhost") # Now respecting env var again or defaulting
        self._port = os.getenv("MILVUS_PORT", "19530")
        self._alias = "default"
        self._collection: Collection | None = None

    def _get_collection_schema(self) -> CollectionSchema:
        # Define fields with original_text as primary key to enforce uniqueness
        fields = [
            FieldSchema(name=MILVUS_TEXT_FIELD, dtype=DataType.VARCHAR, max_length=5000, is_primary=True, auto_id=False),
            FieldSchema(name=MILVUS_VECTOR_FIELD, dtype=DataType.FLOAT_VECTOR, dim=EMBEDDING_DIMENSION),
            FieldSchema(name=MILVUS_ELEMENT_TYPE_FIELD, dtype=DataType.VARCHAR, max_length=32) # 'Node', 'Relationship', 'CategoryNode'
        ]
        # Schema description updated
        schema = CollectionSchema(fields, description="Knowledge Vectors: Text Embeddings Only")  
        return schema

    async def create_collection_if_not_exists(self):
        """Creates the Milvus collection and index if they don't exist."""
        try:
            has_collection = await asyncio.to_thread(utility.has_collection, MILVUS_COLLECTION_NAME, using=self._alias)
            if not has_collection:
                logger.info(f"Milvus collection '{MILVUS_COLLECTION_NAME}' not found. Creating with new simplified schema (text embeddings only)...")
                schema = self._get_collection_schema()
                self._collection = await asyncio.to_thread(_sync_create_collection, self._alias, schema)
                await asyncio.to_thread(_sync_create_index, self._collection, MILVUS_VECTOR_FIELD)
                if utility.load_state(MILVUS_COLLECTION_NAME) != "loaded":
                    self._collection.load()
                    utility.wait_for_loading_complete(MILVUS_COLLECTION_NAME)
                logger.info(f"Milvus collection '{MILVUS_COLLECTION_NAME}' created and loaded.")
            else:
                logger.info(f"Milvus collection '{MILVUS_COLLECTION_NAME}' already exists. Checking schema...")
                self._collection = Collection(name=MILVUS_COLLECTION_NAME, using=self._alias)
                # Schema check: Ensure only expected fields exist
                schema_dict = self._collection.schema.to_dict()
                schema_fields = {field['name']: field['type'] for field in schema_dict.get('fields', [])}
                expected_fields = {MILVUS_TEXT_FIELD, MILVUS_VECTOR_FIELD, MILVUS_ELEMENT_TYPE_FIELD}
                actual_field_names = set(schema_fields.keys())

                if actual_field_names != expected_fields:
                    missing = expected_fields - actual_field_names
                    extra = actual_field_names - expected_fields
                    logger.critical(f"Existing Milvus collection '{MILVUS_COLLECTION_NAME}' schema mismatch. Dropping and recreating to enforce uniqueness.")
                    # Drop and recreate collection with updated schema
                    try:
                        await asyncio.to_thread(utility.drop_collection, MILVUS_COLLECTION_NAME, using=self._alias)
                        logger.info(f"Dropped Milvus collection '{MILVUS_COLLECTION_NAME}'.")
                    except Exception as drop_err:
                        logger.error(f"Failed to drop mismatched Milvus collection '{MILVUS_COLLECTION_NAME}': {drop_err}", exc_info=True)
                        raise
                    # Recreate with correct schema and index
                    schema = self._get_collection_schema()
                    self._collection = await asyncio.to_thread(_sync_create_collection, self._alias, schema)
                    await asyncio.to_thread(_sync_create_index, self._collection, MILVUS_VECTOR_FIELD)
                    if utility.load_state(MILVUS_COLLECTION_NAME) != "loaded":
                        self._collection.load()
                        utility.wait_for_loading_complete(MILVUS_COLLECTION_NAME)
                    logger.info(f"Recreated Milvus collection '{MILVUS_COLLECTION_NAME}' with updated schema and loaded.")
                    return
                else:
                    logger.info(f"Existing schema matches expectations (text embeddings only).")

                has_index = await asyncio.to_thread(self._collection.has_index)
                if not has_index:
                    logger.warning(f"Milvus index '{MILVUS_INDEX_NAME}' not found on existing collection. Creating...")
                    await asyncio.to_thread(_sync_create_index, self._collection, MILVUS_VECTOR_FIELD)
                else:
                     logger.info(f"Milvus index '{MILVUS_INDEX_NAME}' already exists.")
                
                if utility.load_state(MILVUS_COLLECTION_NAME) != "loaded":
                     logger.info(f"Loading existing Milvus collection '{MILVUS_COLLECTION_NAME}'...")
                     self._collection.load()
                     utility.wait_for_loading_complete(MILVUS_COLLECTION_NAME)
                     logger.info(f"Milvus collection '{MILVUS_COLLECTION_NAME}' loaded.")

        except MilvusException as e:
            logger.error(f"Error checking or creating Milvus collection/index: {e}", exc_info=True)
            raise

    async def connect(self):
        """Connects to Milvus and ensures the collection exists."""
        try:
            logger.info(f"Attempting to connect to Milvus at {self._host}:{self._port}")
            connections.connect(
                alias=self._alias,
                host=self._host,
                port=self._port
            )
            # Check connection status using a simple server command
            try:
                # Use utility.get_server_version() or similar robust check
                server_version = await asyncio.to_thread(utility.get_server_version, using=self._alias)
                logger.info(f"Successfully connected to Milvus ({self._alias}) at {self._host}:{self._port}. Server version: {server_version}")
                # Ensure collection and index exist only after confirming connection
                await self.create_collection_if_not_exists()
            except Exception as connection_check_err:
                 logger.error(f"Milvus connection check failed after connect call: {connection_check_err}", exc_info=True)
                 try:
                     connections.disconnect(self._alias) # Attempt to clean up connection
                 except Exception: pass
                 raise ConnectionError("Failed to establish a healthy connection to Milvus")

        except MilvusException as e:
            logger.error(f"Milvus connection or setup error: {e}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"An unexpected error occurred during Milvus connection/setup: {e}", exc_info=True)
            raise

    def close(self):
        """Disconnect from Milvus alias if connected."""
        try:
            if self.is_connected():
                # Release collection potentially? Check pymilvus docs if needed
                # self._collection.release() ?
                connections.disconnect(self._alias)
                logger.info(f"Disconnected from Milvus ({self._alias}).")
            else:
                 logger.info(f"Milvus ({self._alias}) already disconnected or connection was not established.")
        except MilvusException as e:
            logger.error(f"Error disconnecting from Milvus: {e}", exc_info=True)
        except Exception as e:
            logger.error(f"An unexpected error occurred during Milvus disconnection: {e}", exc_info=True)

    def is_connected(self) -> bool:
        """Return True if the Milvus connection is currently active."""
        try:
            conn_addr = utility.get_connection_addr(self._alias)
            return conn_addr is not None and conn_addr.get('address') == f"{self._host}:{self._port}"
        except Exception:
            return False # Any error likely means not connected properly

    async def insert_vectors(self, vectors_data: List[Dict[str, Any]]) -> List[Any]:
        """Insert multiple vectors with metadata into Milvus in a background thread and return IDs."""
        if not self._collection:
            logger.error("Milvus collection is not initialized. Cannot insert vectors.")
            raise ConnectionError("Milvus collection not available")
        if not vectors_data:
            logger.warning("insert_vectors called with empty data list.")
            return []
        
        # Prepare data in the format Milvus expects (list of dicts matching schema fields)
        prepared_data = []
        for item in vectors_data:
            # Only include fields defined in the simplified schema, ensure text is lowercase
            data_entry = {
                MILVUS_VECTOR_FIELD: item["embedding"],
                MILVUS_ELEMENT_TYPE_FIELD: item["element_type"],
                MILVUS_TEXT_FIELD: item["original_text"].lower()
            }
            prepared_data.append(data_entry)

        try:
            # Run the insertion in a separate thread
            inserted_ids = await asyncio.to_thread(
                _sync_insert_vectors, self._collection, prepared_data
            )
            return inserted_ids
        except Exception as e:
            # Error is logged within _sync_insert_vectors or asyncio wrapper
            logger.error(f"Failed to insert vectors via thread: {e}")
            return [] # Return empty list on failure

    async def search_vectors(self, query_embeddings: List[List[float]], top_k: int = 5, similarity_threshold: float = 0.75) -> List[Dict[str, Any]]:
        """Perform a vector similarity search in Milvus in a background thread."""
        if not self._collection:
            logger.error("Milvus collection is not initialized. Cannot search vectors.")
            raise ConnectionError("Milvus collection not available")
        if not query_embeddings:
            logger.warning("search_vectors called with empty query embeddings.")
            return []
        
        try:
            # Run the search in a separate thread
            search_results = await asyncio.to_thread(
                _sync_search_vectors, self._collection, query_embeddings, top_k, similarity_threshold
            )
            return search_results
        except Exception as e:
            # Error is logged within _sync_search_vectors or asyncio wrapper
            logger.error(f"Failed to search vectors via thread: {e}")
            return [] # Return empty list on failure

    async def get_vector_id_by_text(self, text: str) -> Optional[int]:
        """Fetch the ID of a vector in Milvus by exact original_text match."""
        if not self._collection:
            logger.error("Milvus collection is not initialized. Cannot search vectors by text.")
            raise ConnectionError("Milvus collection not available")
        
        # Normalize text before passing to sync function
        normalized_text = text.strip().lower() if text else ""
        if not normalized_text:
            logger.warning("get_vector_id_by_text called with empty/whitespace text.")
            return None
        
        try:
            original_text = await asyncio.to_thread(
                _sync_get_vector_id_by_text, self._collection, normalized_text
            )
            return original_text
        except Exception as e:
            logger.error(f"Failed to get vector ID by text '{normalized_text[:50]}...' via thread: {e}")
            return None

# Create a singleton instance of the service
milvus_service = MilvusService() 