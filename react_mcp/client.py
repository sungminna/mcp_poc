from dotenv import load_dotenv
import os 
import asyncio

load_dotenv()


from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent

from langchain_openai import ChatOpenAI
model = ChatOpenAI(model="gpt-4o")

async def main():
    async with MultiServerMCPClient(
        {

        }
    ) as client:
        agent = create_react_agent(model, client.get_tools())
        math_response = await agent.ainvoke({"messages": "what's (3 + 5) x 12?"})
        weather_response = await agent.ainvoke({"messages": "what is the weather in nyc?"})
        # You might want to print the responses
        print("Math response:", math_response)
        print("Weather response:", weather_response)

if __name__ == "__main__":
    asyncio.run(main())