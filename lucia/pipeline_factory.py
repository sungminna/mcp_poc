"""
Provides factory functions using lru_cache to create and retrieve singleton 
instances of various components (clients, stores, extractors, pipelines) 
used within the Lucia application. This ensures efficient resource management 
by reusing component instances.
"""
from functools import lru_cache

from .pipelines.knowledge_pipeline import KnowledgePipeline
from .pipelines.search_pipeline import SearchPipeline
from .clients.openai_client import OpenAIClient
from .extractors.openai_extractors import OpenAIKeywordExtractor, OpenAIInfoExtractor
from .embeddings.openai_embedding_client import OpenAIEmbeddingClient
from .vectorstores.milvus_vector_store import MilvusVectorStore
from .stores.info_store import InfoStore
from .stores.info_store_neo4j import Neo4jInfoStore
from .stores.info_store_clickhouse import ClickHouseInfoStore

@lru_cache()
def get_embedding_client() -> OpenAIEmbeddingClient:
    # Single instance of OpenAIEmbeddingClient with Redis caching enabled
    return OpenAIEmbeddingClient(use_cache=True)

@lru_cache()
def get_llm_client() -> OpenAIClient:
    # Single instance of OpenAIClient for extractors
    return OpenAIClient()

@lru_cache()
def get_keyword_extractor() -> OpenAIKeywordExtractor:
    # Single instance of OpenAIKeywordExtractor for keyword extraction
    return OpenAIKeywordExtractor(client=get_llm_client())

@lru_cache()
def get_info_extractor() -> OpenAIInfoExtractor:
    # Single instance of OpenAIInfoExtractor for personal info extraction
    return OpenAIInfoExtractor(client=get_llm_client())

@lru_cache()
def get_vector_store() -> MilvusVectorStore:
    # Single instance of MilvusVectorStore
    return MilvusVectorStore()

@lru_cache()
def get_neo4j_info_store() -> Neo4jInfoStore:
    # Single instance of Neo4jInfoStore
    return Neo4jInfoStore()

@lru_cache()
def get_clickhouse_info_store() -> ClickHouseInfoStore:
    # Single instance of ClickHouseInfoStore
    return ClickHouseInfoStore()

@lru_cache()
def get_info_store() -> InfoStore:
    # Default to Neo4j info store (singleton)
    return get_clickhouse_info_store()
    # return get_neo4j_info_store()

@lru_cache()
def get_knowledge_pipeline() -> KnowledgePipeline:
    # Single instance of KnowledgePipeline with shared, reused dependencies
    return KnowledgePipeline(
        keyword_extractor=get_keyword_extractor(),
        embedding_client=get_embedding_client(),
        vector_store=get_vector_store(),
        info_extractor=get_info_extractor(),
        info_store=get_info_store(),
    )

@lru_cache()
def get_search_pipeline() -> SearchPipeline:
    # Single instance of SearchPipeline with shared dependencies
    return SearchPipeline(
        keyword_extractor=get_keyword_extractor(),
        embedding_client=get_embedding_client(),
        vector_store=get_vector_store(),
        info_extractor=get_info_extractor(),
        info_store=get_info_store(),
    ) 