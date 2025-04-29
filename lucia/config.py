from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    # OpenAI settings
    openai_api_key: str
    openai_model_name: str = "gpt-4.1-nano"
    embedding_model_name: str = "text-embedding-3-small"

    # Redis caching settings
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

    # Pydantic v2 settings configuration: load .env and ignore unknown env vars
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

# Instantiate settings for use across the package
settings = Settings() 