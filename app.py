import streamlit as st
import asyncio
import traceback

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from langgraph.prebuilt import create_react_agent
from langchain_mcp_adapters.tools import load_mcp_tools
from langchain_ollama.chat_models import ChatOllama
import sys

if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

# Model name to use with Ollama
MODEL_NAME = 'qwen2.5-coder:7b'

# Initialize Ollama chat model
model = ChatOllama(model=MODEL_NAME)

# Function to handle user query and return agent's response
async def call_ollama(user_query):
    server_params = StdioServerParameters(
        command="python",
        args=["mcp_server.py"]
    )
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await load_mcp_tools(session)
            # print("TOOLS:", tools)
            agent = create_react_agent(model, tools)
            response = await agent.ainvoke({"messages": user_query})
            print("RESPONSE:", response)
            return response

# Main Streamlit app
async def main():
    st.set_page_config(page_title="Natural Language to SQL", page_icon="🧠")
    st.title("🧠 Natural Language to SQL with Ollama")
    st.write("Type your question in natural language and get SQL-powered answers!")

    nl_query = st.text_input("Ask your question about the database:")

    if nl_query:
        try:
            with st.spinner("Running SQL query..."):
                result = await call_ollama(nl_query+" in the table transaction_score")
            st.success("Query executed successfully!")

            for message in result['messages']:
                st.text(message.content)
        except Exception as e:
            st.error(f"Error running query: {e}")
            st.text("Traceback:")
            st.code(traceback.format_exc())

# Run the app
if __name__ == "__main__":
    asyncio.run(main())
