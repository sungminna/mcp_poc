"""
Configuration module for Lucia application.
Defines environment-based settings for OpenAI, Redis caching, vector databases (Milvus),
graph databases (Neo4j, ClickHouse), and embedding models.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    """
    Application settings loaded from environment variables or .env file.

    Attributes:
        openai_api_key (str): API key for OpenAI service.
        openai_model_name (str): Default model name for chat/completion.
        embedding_model_name (str): Default model for text embeddings.

        use_redis_cache (bool): Flag to enable Redis caching of embeddings.
        redis_host (str): Redis server hostname.
        redis_port (int): Redis server port.
        redis_db (int): Redis database index.
        redis_password (Optional[str]): Redis authentication password.
        cache_ttl_seconds (Optional[int]): Time-to-live for cache entries (seconds).

        milvus_host (str): Milvus vector store hostname.
        milvus_port (int): Milvus vector store port.

        neo4j_uri (str): Neo4j database URI.
        neo4j_user (str): Username for Neo4j.
        neo4j_password (str): Password for Neo4j.
        neo4j_database (str): Default Neo4j database name.

        clickhouse_uri (str): ClickHouse HTTP URI.
        clickhouse_user (str): Username for ClickHouse.
        clickhouse_password (str): Password for ClickHouse.
        clickhouse_database (str): Default ClickHouse database name.
    """
    openai_api_key: str
    openai_model_name: str = "gpt-4.1-nano"
    embedding_model_name: str = "text-embedding-3-small"
    use_redis_cache: bool = False
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: Optional[str] = None
    cache_ttl_seconds: Optional[int] = None

    # Milvus settings
    milvus_host: str = "localhost"
    milvus_port: int = 19530

    # Neo4j settings
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "password"
    neo4j_database: str = "neo4j"

    # ClickHouse settings
    clickhouse_uri: str = "http://localhost:8123"
    clickhouse_user: str = "default"
    clickhouse_password: str = "password"
    clickhouse_database: str = "default"

    # Pydantic v2 settings configuration: load .env and ignore unknown env vars
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

# Instantiate global settings object for access throughout the Lucia package
settings = Settings() 