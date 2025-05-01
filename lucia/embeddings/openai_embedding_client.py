from openai import OpenAI
from typing import List
import hashlib
import json
import redis.asyncio as aioredis
from ..config import settings

from .embedding_client import EmbeddingClient

class OpenAIEmbeddingClient(EmbeddingClient):
    def __init__(self, api_key: str = None, model_name: str = "text-embedding-3-small", use_cache: bool = False, redis_host: str = None, redis_port: int = None, redis_db: int = 0, redis_password: str = None, cache_ttl_seconds: int = None):
        """
        Initialize OpenAI embedding client with an API key and model name.
        Optionally enable Redis caching of embeddings by setting use_cache=True.
        Redis connection parameters can be provided or loaded from REDIS_* environment variables.
        Cache time-to-live (TTL) in seconds can be set via cache_ttl_seconds; if None, entries never expire.
        """
        self.api_key = api_key or settings.openai_api_key
        if not self.api_key:
            raise ValueError("OpenAI API key must be provided via api_key parameter or OPENAI_API_KEY env var.")
        self.client = OpenAI(api_key=self.api_key)
        self.model_name = model_name or settings.embedding_model_name
        self.use_cache = use_cache or settings.use_redis_cache
        # Optional TTL (in seconds) for cached embeddings; None means no expiration
        self.cache_ttl_seconds = cache_ttl_seconds or settings.cache_ttl_seconds
        if self.use_cache:
            # Initialize Redis client for caching using centralized settings
            host = redis_host or settings.redis_host
            port = redis_port or settings.redis_port
            db = redis_db or settings.redis_db
            password = redis_password or settings.redis_password
            self.redis_client = aioredis.Redis(
                host=host,
                port=port,
                db=db,
                password=password,
                decode_responses=True
            )

    def _cache_key(self, text: str) -> str:
        # Generate a Redis key for caching embeddings of a text
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        return f"emb:{self.model_name}:{digest}"

    async def embed_text(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a list of texts using OpenAI API, with optional Redis caching.
        """
        if not texts:
            return []
        results: List[List[float]] = [None] * len(texts)
        texts_to_fetch: List[str] = []
        indices_to_fetch: List[int] = []

        if self.use_cache:
            # Attempt to retrieve embeddings from cache
            for idx, text in enumerate(texts):
                key = self._cache_key(text)
                cached = await self.redis_client.get(key)
                if cached:
                    try:
                        results[idx] = json.loads(cached)
                    except json.JSONDecodeError:
                        results[idx] = None
                if results[idx] is None:
                    texts_to_fetch.append(text)
                    indices_to_fetch.append(idx)
        else:
            texts_to_fetch = texts
            indices_to_fetch = list(range(len(texts)))

        # Fetch embeddings from OpenAI for missing texts
        if texts_to_fetch:
            response = self.client.embeddings.create(
                model=self.model_name,
                input=texts_to_fetch
            )
            new_embeddings = [data.embedding for data in response.data]
            if self.use_cache:
                # Cache the new embeddings with optional TTL
                for text, emb in zip(texts_to_fetch, new_embeddings):
                    key = self._cache_key(text)
                    if self.cache_ttl_seconds is not None:
                        await self.redis_client.set(key, json.dumps(emb), ex=self.cache_ttl_seconds)
                    else:
                        await self.redis_client.set(key, json.dumps(emb))
            for idx, emb in zip(indices_to_fetch, new_embeddings):
                results[idx] = emb
        return results 