from abc import ABC, abstractmethod
from typing import Type, List, Dict, Any
from pydantic import BaseModel

class LLMClient(ABC):
    @abstractmethod
    async def ask(
        self,
        input_list: List[Dict[str, str]],
        output_format: Type[BaseModel]
    ) -> Dict[str, Any]:
        """
        Sends a list of messages (role/content) to the LLM and returns the raw JSON response string.
        input_list: list of {'role': <role>, 'content': <text>} dicts.
        output_format: Pydantic model class for downstream parsing—ignored by client implementation.
        Returns the JSON output string from the LLM.
        """
        pass 