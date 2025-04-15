from dotenv import load_dotenv
import os 
import asyncio

load_dotenv()

from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI
model = ChatOpenAI(model="gpt-4.1-nano")


async def llm_ask(question: str):
    async with MultiServerMCPClient(
        {
            "math": {
                "command": "python",
                # Make sure to update to the full absolute path to your math_server.py file
                "args": ["math_server.py"], # Consider making this configurable
                "transport": "stdio",
            },
            "weather": {
                # make sure you start your weather server on port 8000 (updated port)
                "url": "http://localhost:8000/sse", # Consider making this configurable
                "transport": "sse",
            }
        }
    ) as client:
        agent = create_react_agent(model, client.get_tools())
        math_response = await agent.ainvoke({"messages": question})
        return {"response": math_response} 