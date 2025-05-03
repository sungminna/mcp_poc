from agents import Agent, Runner
from openai.types.responses import ResponseTextDeltaEvent
import asyncio
import os
from lucia.config import settings
from lucia.prompts import chitchat_agent_system_prompt

from lucia.pipeline_factory import get_knowledge_pipeline, get_search_pipeline

# PYTHONPATH=.. poetry run python agents/chitchat.py
"""
Module for the interactive ChitChat agent integrating personal info and keyword pipelines for context-aware dialogue.
"""
class ChitChatAgent:
    """Conversational agent that maintains user context, uses pipelines, and streams LLM responses."""
    def __init__(self, name: str = "ChitChat", model: str = None, temperature: float = 0.7):
        os.environ.setdefault("OPENAI_API_KEY", settings.openai_api_key)
        self.model = model or settings.openai_model_name
        self.agent = Agent(
            name=name,
            model=self.model,
            instructions=chitchat_agent_system_prompt
        )
        self.conversation = []

        # Use singleton pipelines from factory
        self.knowledge_pipeline = get_knowledge_pipeline()
        self.search_pipeline = get_search_pipeline()

    async def run(self):
        """Read user messages, enrich with personal context, stream LLM responses, and persist new info."""
        print("Chat agent initialized. Type your message (or empty input to quit).")
        while True:
            user_input = input("User: ")
            if not user_input:
                print("Exiting chat.")
                break
            # Append user message to conversation history
            self.conversation.append({"role": "user", "content": user_input})
            res = await self.search_pipeline.process(user_input, "test_user")
            relationships = res['relationships']            # Build structured context with personal information as a system message
            print(res)
            info_content = (
                "Here is some relevant personal information about the user which is might be relevant to the conversation:\n"
                + "\n".join(f"- {rel}" for rel in relationships)
            )
            context = [{"role": "system", "content": info_content}] + self.conversation
            # Stream the agent response with configured temperature
            stream_result = Runner.run_streamed(
                self.agent,
                context,
            )
            print("Bot: ", end="", flush=True)
            async for event in stream_result.stream_events():
                if event.type == "raw_response_event" and isinstance(event.data, ResponseTextDeltaEvent):
                    print(event.data.delta, end="", flush=True)
            print()  # newline after complete response
            # Update history for next turn
            self.conversation = stream_result.to_input_list()
            saved_res = await self.knowledge_pipeline.process(user_input, "test_user")
            print(saved_res)
if __name__ == "__main__":
    asyncio.run(ChitChatAgent().run())
