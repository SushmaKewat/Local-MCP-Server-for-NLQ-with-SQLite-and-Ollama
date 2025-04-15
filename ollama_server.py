# import requests
# import asyncio

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from langgraph.prebuilt import create_react_agent
from langchain_mcp_adapters.tools import load_mcp_tools
from langchain_ollama.chat_models import ChatOllama

# OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = 'qwen2.5-coder:7b'

model = ChatOllama(model=MODEL_NAME)
    
async def call_ollama(user_query):
    server_params = StdioServerParameters(
        command="python",
        args=["mcp_server.py"]
    ) 
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            tools = await load_mcp_tools(session)
            
            agent = create_react_agent(model, tools)
            
            response = await agent.ainvoke({"messages": user_query})
            
            return response
            
