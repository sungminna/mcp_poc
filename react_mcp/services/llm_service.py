from dotenv import load_dotenv
import os 
import asyncio
from core.depends import langfuse_handler

load_dotenv()

from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI
from routers.prompts import llm_chat_prompt

model = ChatOpenAI(model="gpt-4.1-nano")

'''
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
'''


async def llm_ask(question: str):
    async with MultiServerMCPClient(
        {

        }
    ) as client:
        agent = create_react_agent(model, client.get_tools())
        # build messages from ChatPromptTemplate
        prompt_obj = llm_chat_prompt.format_prompt(user_message=question)
        # convert ChatPromptTemplate messages to dicts
        messages = [{"role": msg.type, "content": msg.content} for msg in prompt_obj.messages]
        response = await agent.ainvoke({"messages": messages}, config={"callbacks": [langfuse_handler]})
        return {"response": response} 