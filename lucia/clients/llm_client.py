"""
Defines the abstract base class (interface) for interacting with Large Language Models (LLMs).
"""
from abc import ABC, abstractmethod
from typing import Type, List, Dict, Any
from pydantic import BaseModel

class LLMClient(ABC):
    @abstractmethod
    async def ask(
        self,
        input_list: List[Dict[str, str]],
        output_format: Type[BaseModel]
    ) -> BaseModel:
        """
        Sends a list of messages (role/content) to the LLM and returns the parsed response.

        Args:
            input_list: List of {'role': <role>, 'content': <text>} dicts.
            output_format: Pydantic model class defining the expected structure of the LLM response.

        Returns:
            An instance of the provided Pydantic model (output_format) populated with the LLM's response.
        """
        pass 