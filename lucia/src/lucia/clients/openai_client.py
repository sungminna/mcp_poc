"""
OpenAIClient implementation using the AsyncOpenAI Responses API.
Sends message lists to the model and parses outputs into Pydantic models.
"""
from typing import Type, List, Dict, Any
from openai import AsyncOpenAI
from pydantic import BaseModel
from .llm_client import LLMClient
from ..config import settings


class OpenAIClient(LLMClient):
    def __init__(self, api_key: str = None, model_name: str = None):
        """
        Initialize the OpenAI client for structured response parsing.

        Args:
            api_key (str, optional): OpenAI API key (overrides environment setting).
            model_name (str, optional): Model name for the Responses API.
        Raises:
            ValueError: If no API key is provided or configured.
        """
        self.api_key = api_key or settings.openai_api_key
        if not self.api_key:
            raise ValueError("OpenAI API key must be provided via api_key parameter or environment variable.")
        self.client = AsyncOpenAI(api_key=self.api_key)
        self.model_name = model_name or settings.openai_model_name

    async def ask(
        self,
        input_list: List[Dict[str, str]],
        output_format: Type[BaseModel]
    ) -> BaseModel:
        """
        Send messages to the model and parse the JSON output into a Pydantic model.

        Args:
            input_list (List[Dict[str, str]]): Sequence of role/content message dicts.
            output_format (Type[BaseModel]): Pydantic model class for response parsing.

        Returns:
            BaseModel: Parsed response instance.
        """
        # Use the last message content as the input
        response = await self.client.responses.parse(
            model=self.model_name,
            input=input_list,
            text_format=output_format,
        )
        return response.output_parsed