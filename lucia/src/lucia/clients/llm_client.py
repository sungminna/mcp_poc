"""
LLMClient interface module.

Defines an abstract base class for communicating with Large Language Models.
Implementations must provide an `ask` method to send messages and receive structured responses.
"""
from abc import ABC, abstractmethod
from typing import Type, List, Dict, Any
from pydantic import BaseModel

class LLMClient(ABC):
    """
    Abstract base class for LLM client implementations.

    Provides a contract for sending messages (`ask`) and receiving parsed responses.
    """
    @abstractmethod
    async def ask(
        self,
        input_list: List[Dict[str, str]],
        output_format: Type[BaseModel]
    ) -> BaseModel:
        """
        Send a sequence of messages to the LLM and parse the JSON output.

        Args:
            input_list (List[Dict[str, str]]): Conversation messages with 'role' and 'content'.
            output_format (Type[BaseModel]): Pydantic class describing expected response schema.

        Returns:
            BaseModel: Parsed model instance with the LLM's response.
        """
        pass 