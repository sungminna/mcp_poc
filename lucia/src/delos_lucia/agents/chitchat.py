from agents import Agent, Runner
from openai.types.responses import ResponseTextDeltaEvent
import asyncio
import os
from lucia.config import settings
from lucia.prompts import chitchat_agent_system_prompt

from lucia.pipeline_factory import get_knowledge_pipeline, get_search_pipeline

"""ChitChatAgent module.

Provides an interactive conversational AI agent that leverages personal information
and keyword pipelines to deliver context-aware dialogue.

Usage:
    PYTHONPATH=.. poetry run python agents/chitchat.py
"""

class ChitChatAgent:
    """Conversational agent that maintains user context, enriches messages with personal info,
    streams LLM responses, and persists new information."""
    def __init__(self, name: str = "ChitChat", model: str = None, temperature: float = 0.7):
        os.environ.setdefault("OPENAI_API_KEY", settings.openai_api_key)
        """Initialize agent components and conversation context."""
        self.model = model or settings.openai_model_name
        self.agent = Agent(
            name=name,
            model=self.model,
            instructions=chitchat_agent_system_prompt
        )
        self.conversation = []  # message history for context

        # Load singleton pipelines for context enrichment and persistence
        self.knowledge_pipeline = get_knowledge_pipeline()
        self.search_pipeline = get_search_pipeline()

    async def run(self):
        """Start interactive loop: read user input, enrich context, stream responses, and save new info."""
        print("Chat agent initialized. Type your message (or empty input to quit).")
        while True:
            user_input = input("User: ")
            if not user_input:
                print("Exiting chat.")
                break
            # Record user message
            self.conversation.append({"role": "user", "content": user_input})
            # Retrieve contextual relationships via search pipeline
            res = await self.search_pipeline.process(user_input, "test_user")
            relationships = res['relationships']
            # Prepare system context with personal info descriptions
            info_content = (
                "Here is some relevant personal information about the user which is might be relevant to the conversation:\n"
                + "\n".join(f"- {rel}" for rel in relationships)
            )
            context = [{"role": "system", "content": info_content}] + self.conversation
            # Stream LLM response with enriched context
            stream_result = Runner.run_streamed(
                self.agent,
                context,
            )
            print("Bot: ", end="", flush=True)
            async for event in stream_result.stream_events():
                if event.type == "raw_response_event" and isinstance(event.data, ResponseTextDeltaEvent):
                    print(event.data.delta, end="", flush=True)
            print()  # newline after complete response
            # Update conversation history for next turn
            self.conversation = stream_result.to_input_list()
            # Persist any newly extracted personal information
            await self.knowledge_pipeline.process(user_input, "test_user")

if __name__ == "__main__":
    asyncio.run(ChitChatAgent().run())
