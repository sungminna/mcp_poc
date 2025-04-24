from pydantic_settings import BaseSettings
from pydantic import AnyUrl, ConfigDict
from typing import List

class Settings(BaseSettings):
    model_config = ConfigDict(env_file=".env", extra="ignore")
    SECRET_KEY: str = "default_secret_key_needs_to_be_changed"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    DATABASE_URL: AnyUrl
    RATE_LIMIT_CHAT: str = "30/minute"
    RATE_LIMIT_LOGIN: str = "10/minute"
    RATE_LIMIT_REGISTER: str = "5/hour"
    LANGFUSE_SECRET_KEY: str
    LANGFUSE_PUBLIC_KEY: str
    LANGFUSE_HOST: AnyUrl
    CORS_ALLOW_ORIGINS: List[str] = ["*"]
    # Additional environment variables for external services
    openai_api_key: str
    neo4j_uri: str
    neo4j_username: str
    neo4j_password: str
    redis_url: str = "redis://localhost:6379"

settings = Settings()

# Module-level aliases for backward compatibility
SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES
DATABASE_URL = settings.DATABASE_URL
RATE_LIMIT_CHAT = settings.RATE_LIMIT_CHAT
RATE_LIMIT_LOGIN = settings.RATE_LIMIT_LOGIN
RATE_LIMIT_REGISTER = settings.RATE_LIMIT_REGISTER
LANGFUSE_SECRET_KEY = settings.LANGFUSE_SECRET_KEY
LANGFUSE_PUBLIC_KEY = settings.LANGFUSE_PUBLIC_KEY
LANGFUSE_HOST = settings.LANGFUSE_HOST
CORS_ALLOW_ORIGINS = settings.CORS_ALLOW_ORIGINS 