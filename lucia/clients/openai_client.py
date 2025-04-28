from typing import Type, List, Dict, Any
import os
from openai import OpenAI
from pydantic import BaseModel
from .llm_client import LLMClient


class OpenAIClient(LLMClient):
    def __init__(self, api_key: str = None, model_name: str = "gpt-4.1-nano"):
        """
        Initialize AsyncOpenAI client for the Responses API.
        If api_key is not provided, reads from OPENAI_API_KEY env var.
        model_name should be a text model supporting the Responses API (e.g., 'gpt-4o').
        """
        key = api_key or os.getenv("OPENAI_API_KEY")
        if not key:
            raise ValueError(
                "OpenAI API key must be provided via api_key parameter or OPENAI_API_KEY env var."
            )
        self.client = OpenAI(api_key=key)
        self.model_name = model_name

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