from typing import List, Dict, Any, Optional
from .vector_store import VectorStore
import asyncio
from ..config import settings
from pymilvus import (
    connections, utility, Collection, CollectionSchema, FieldSchema, DataType, Index
)
from pymilvus.exceptions import MilvusException

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
    def __init__(self):
        self._host = settings.milvus_host
        self._port = settings.milvus_port
        self._alias = "default"
        self._collection: Optional[Collection] = None
        self._connect_task = asyncio.create_task(self._connect_and_prepare())

    async def _connect_and_prepare(self):
        try:
            connections.connect(alias=self._alias, host=self._host, port=self._port)
            await asyncio.to_thread(self._ensure_collection_and_index)
        except Exception as e:
            raise RuntimeError(f"Failed to connect or prepare Milvus: {e}")

    def _ensure_collection_and_index(self):
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

    async def insert_vectors(self, data: List[Dict[str, Any]]) -> List[Any]:
        await self._connect_task
        if not data:
            return []
        prepared_data = []
        for item in data:
            prepared_data.append({
                MILVUS_VECTOR_FIELD: item["embedding"],
                MILVUS_ELEMENT_TYPE_FIELD: item["element_type"],
                MILVUS_TEXT_FIELD: item["original_text"].lower()
            })
        try:
            result = await asyncio.to_thread(self._collection.insert, prepared_data)
            await asyncio.to_thread(self._collection.flush)
            return result.primary_keys
        except Exception as e:
            raise RuntimeError(f"Failed to insert vectors: {e}")

    async def search_vectors(self, query_embeddings: List[List[float]], top_k: int = 5, similarity_threshold: float = 0.75) -> List[Dict[str, Any]]:
        await self._connect_task
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
            unique_texts = set()
            for hits in results:
                for hit in hits:
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
            processed_hits.sort(key=lambda x: x["score"], reverse=True)
            return processed_hits[:top_k]
        except Exception as e:
            raise RuntimeError(f"Failed to search vectors: {e}")

    async def get_vector_id_by_text(self, text: str) -> Optional[Any]:
        await self._connect_task
        normalized_text = text.strip().lower() if text else ""
        if not normalized_text:
            return None
        expr = f'{MILVUS_TEXT_FIELD} == "{normalized_text.replace("\"", "\\\"")}"'
        search_params = {
            "data": [],
            "anns_field": MILVUS_VECTOR_FIELD,
            "param": {},
            "limit": 1,
            "expr": expr,
            "output_fields": [MILVUS_TEXT_FIELD]
        }
        try:
            results = await asyncio.to_thread(self._collection.search, **search_params)
            if results and results[0]:
                first_hit = results[0][0]
                return first_hit.entity.get(MILVUS_TEXT_FIELD)
            return None
        except Exception:
            return None 