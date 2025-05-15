from langchain_core.messages import AnyMessage
from langchain_core.runnables import RunnableConfig
from langgraph.prebuilt import create_react_agent
from langchain.chat_models import init_chat_model

from pydantic import BaseModel
from typing import Any

from langmem.short_term import SummarizationNode
from langgraph.prebuilt.chat_agent_executor import AgentState
from langchain_core.messages.utils import trim_messages, count_tokens_approximately
from langgraph.checkpoint.postgres import PostgresSaver
from asgiref.sync import sync_to_async

import os
import dotenv

dotenv.load_dotenv()
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")

# Build Postgres connection string from environment
DB_USER = os.getenv("POSTGRES_USER", os.getenv("DB_USER", "postgres"))
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", os.getenv("DB_PASSWORD", "password"))
DB_HOST = os.getenv("POSTGRES_HOST", os.getenv("DB_HOST", "localhost"))
DB_PORT = os.getenv("POSTGRES_PORT", os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("POSTGRES_DB", os.getenv("DB_NAME", "postgres"))
DB_URI = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?sslmode=disable"

# Singleton PostgresSaver for production use
_checkpointer_cm = None
_checkpointer = None

def init_checkpointer():
    """Initialize and return a singleton PostgresSaver instance, running setup only once."""
    global _checkpointer_cm, _checkpointer
    if _checkpointer is None:
        _checkpointer_cm = PostgresSaver.from_conn_string(DB_URI)
        # Enter the context manager to obtain the actual saver instance
        _checkpointer = _checkpointer_cm.__enter__()
        # Setup tables the first time
        _checkpointer.setup()
    return _checkpointer

# Create or retrieve the singleton checkpointer
checkpointer = init_checkpointer()

# Monkey-patch missing async methods on checkpointer
checkpointer.aget_tuple = sync_to_async(checkpointer.get_tuple)
checkpointer.aput = sync_to_async(checkpointer.put)
checkpointer.aput_writes = sync_to_async(lambda *args, **kwargs: None)

llm = init_chat_model(model="gpt-4.1-nano", disable_streaming=False)
tools = []

class ChatResponse(BaseModel):
    response: str

class State(AgentState):
    context: dict[str, Any]
    # Field to hold the parsed structured response from the LLM
    structured_response: ChatResponse

def prompt(state: AgentState, config: RunnableConfig) -> list[AnyMessage]:  
    user_name = config["configurable"].get("user_name")
    system_msg = f"You are a helpful assistant. Address the user as {user_name}."
    return [{"role": "system", "content": system_msg}] + state["messages"]


def pre_model_hook(state):
    trimmed_messages = trim_messages(
        state["messages"],
        strategy="last",
        token_counter=count_tokens_approximately,
        max_tokens=384,
        start_on="human",
        end_on=("human", "tool"),
    )
    return {"llm_input_messages": trimmed_messages}    

# Create the agent with the checkpointer
agent = create_react_agent(
    model=llm,
    tools=tools,
    prompt=prompt,
    pre_model_hook=pre_model_hook,
    state_schema=State,
    checkpointer=checkpointer
)

if __name__ == '__main__':
    # Example CLI streaming test
    config = {"configurable": {"thread_id": "1"}}
    async def main():
        async for token, meta in agent.astream(
            {"messages": [{"role": "user", "content": "who are u"}]},
            config,
            stream_mode="messages"
        ):
            print(token, end="")
        print()
    import asyncio
    asyncio.run(main())