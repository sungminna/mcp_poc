from typing import Type, List, Dict, Any
from openai import OpenAI
from pydantic import BaseModel
from .llm_client import LLMClient
from ..config import settings


class OpenAIClient(LLMClient):
    def __init__(self, api_key: str = None, model_name: str = None):
        """
        Initialize AsyncOpenAI client for the Responses API.
        If api_key is not provided, reads from settings.openai_api_key.
        model_name should be a text model supporting the Responses API.
        """
        self.api_key = api_key or settings.openai_api_key
        if not self.api_key:
            raise ValueError("OpenAI API key must be provided via api_key parameter or environment variable.")
        self.client = OpenAI(api_key=self.api_key)
        self.model_name = model_name or settings.openai_model_name

    async def ask(
        self,
        input_list: List[Dict[str, str]],
        output_format: Type[BaseModel]
    ) -> Dict[str, Any]:
        """
        Sends a series of messages to the LLM via the Responses API.
        input_list: list of {'role': <role>, 'content': <text>} dicts.
        output_format: Pydantic model class for downstream parsing.
        Returns the raw JSON string output by the LLM.
        """
        # Use the last message content as the input
        response = self.client.responses.parse(
            model=self.model_name,
            input=input_list,
            text_format=output_format,
        )
        # Return the raw JSON output
        return response.output_parsed