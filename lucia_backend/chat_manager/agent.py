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
# Initialize a PostgresSaver and ensure tables
saver_cm = PostgresSaver.from_conn_string(DB_URI)
checkpointer = saver_cm.__enter__()
checkpointer.setup()

llm = init_chat_model(model="gpt-4.1-nano")
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

agent = create_react_agent(
    model="gpt-4.1-nano",
    tools=tools,
    prompt=prompt,
    pre_model_hook=pre_model_hook,
    state_schema=State,
    checkpointer=checkpointer, 
    response_format=ChatResponse, 
)

config = {"configurable": {"thread_id": "1"}}

response = agent.invoke(
    {"messages": [{"role": "user", "content": "who are u"}]},
    config=config
)

print(response['structured_response'])