import os
from openai import OpenAI
from typing import List

from .embedding_client import EmbeddingClient

class OpenAIEmbeddingClient(EmbeddingClient):
    def __init__(self, api_key: str = None, model_name: str = "text-embedding-3-small"):
        """
        Initialize OpenAI embedding client with an API key and model name.
        If api_key is not provided, reads from OPENAI_API_KEY env var.
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key must be provided via api_key parameter or OPENAI_API_KEY env var.")
        self.client = OpenAI(api_key=self.api_key)
        self.model_name = model_name

    async def embed_text(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a list of texts using OpenAI API.
        """
        response = self.client.embeddings.create(
            model=self.model_name,
            input=texts
        )
        return [data.embedding for data in response.data] 