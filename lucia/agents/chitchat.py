from agents import Agent, Runner
from openai.types.responses import ResponseTextDeltaEvent
import asyncio
import os
from lucia.config import settings
from lucia.prompts import chitchat_agent_system_prompt

# PYTHONPATH=.. poetry run python agents/chitchat.py
class ChitChatAgent:
    def __init__(self, name: str = "ChitChat", model: str = None, temperature: float = 0.7):
        os.environ.setdefault("OPENAI_API_KEY", settings.openai_api_key)
        self.model = model or settings.openai_model_name    
        self.agent = Agent(
            name=name,
            model=self.model,
            instructions=chitchat_agent_system_prompt
        )
        self.conversation = []

    async def run(self):
        print("Chat agent initialized. Type your message (or empty input to quit).")
        while True:
            user_input = input("User: ")
            if not user_input:
                print("Exiting chat.")
                break
            # Append user message to conversation history
            self.conversation.append({"role": "user", "content": user_input})
            # Stream the agent response with configured temperature
            stream_result = Runner.run_streamed(
                self.agent,
                self.conversation,
            )
            print("Bot: ", end="", flush=True)
            async for event in stream_result.stream_events():
                if event.type == "raw_response_event" and isinstance(event.data, ResponseTextDeltaEvent):
                    print(event.data.delta, end="", flush=True)
            print()  # newline after complete response
            # Update history for next turn
            self.conversation = stream_result.to_input_list()


if __name__ == "__main__":
    asyncio.run(ChitChatAgent().run())
