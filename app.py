import streamlit as st
import asyncio
import traceback
import os

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from langchain_openai import ChatOpenAI

from langgraph.prebuilt import create_react_agent
from langchain_mcp_adapters.tools import load_mcp_tools
from langchain_ollama.chat_models import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

import sys

if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
import dotenv

dotenv.load_dotenv()

# Model name to use with Ollama
REPHRASER_MODEL = 'qwen2.5-coder:7b'
SQL_GENERATOR_MODEL = 'qwen2.5-coder:7b'

# Initialize Ollama chat model
# model = ChatOllama(model=MODEL_NAME)
schema = """CREATE TABLE "transaction_score" (
        "TRANSACTIONID" INTEGER,
        "TRANSACTION_DESC" TEXT,
        "ACCOUNTDOCID" INTEGER,
        "ENTERED_DATE" TEXT,
        "ENTERED_DATE_LOCAL" TEXT,
        "ENTERED_BY_USERID" REAL,
        "POSTED_DATE" TEXT,
        "DEBIT_AMOUNT" REAL,
        "CREDIT_AMOUNT" REAL,
        "IS_REVERSAL" REAL,
        "IS_REVERSED" INTEGER,
        "DOC_TYPE" TEXT,
        "COMPANY_CODE" TEXT,
        "ACCOUNTDOC_CODE" TEXT,
        "ACCOUNT_CODE" INTEGER,
        "ACCOUNT_DESCRIPTION" TEXT,
        "POSTED_BY_USERID" INTEGER,
        "POSTED_BY" TEXT,
        "ENTERED_BY" TEXT,
        "PARKED_DATE" REAL,
        "LINE_ITEM_TEXT" TEXT,
        "HEADER_TEXT" TEXT,
        "BLENDED_RISK_SCORE" REAL,
        "AI_RISK_SCORE" REAL,
        "STAT_SCORE" REAL,
        "RULES_RISK_SCORE" REAL,
        "CONTROL_DEVIATION" TEXT,"MONITORING_DEVIATION" TEXT)"""

# Rephrasing Agent
# async def rephrase_query(user_query):
#     model = ChatOllama(model=REPHRASER_MODEL)

#     # agent = create_react_agent(model)
#     system_prompt = (
#     "You are a helpful assistant that reformulates natural language questions to exactly match a given database schema.\n"
#     "You will be provided with:\n"
#     "1. A user's question written in natural language.\n"
#     "2. A database schema containing table and column names.\n\n"
#     "Your job is to:\n"
#     "- Replace any ambiguous words with the correct column names from the schema.\n"
#     "- Use ONLY the exact column names and table names from the schema.\n"
#     "- Format dates in dd-mm-yyyy or mm-yyyy format.\n"
#     "- Do NOT hallucinate or make up any names.\n"
#     "- Do NOT explain your answer.\n"
#     "- Respond ONLY with the final, rephrased query in plain natural language.\n\n"
#     "⚠️ Important: If you cannot match a column or table, skip rephrasing and respond with: 'Invalid: Column or table not found in schema.'\n\n"
#     "Here is the schema:\n"
#     f"{schema}\n\n"
#     "Begin:"
# )

#     messages = [
#         {"role": "system", "content": system_prompt},
#         {"role": "user", "content": user_query}
#     ]

#     response = await model.ainvoke(messages)
#     print("\n\nREPHRASING RESPONSE:", response)
#     return response

# SQL Generation Agent
# async def generate_sql(refined_query, tools):
    

#     agent = create_react_agent(model, tools)
#     prompt = f"Convert the following natural language query into SQL and query the database:\n{refined_query}"
#     response = await agent.ainvoke({"messages": prompt})
#     print("\n\nSQL RESPONSE:", response)
#     return response['messages'][-1].content

async def rephrase_query(user_query):
    model = ChatOpenAI(model="o3-mini")
    
    chat_template = ChatPromptTemplate.from_template(
            """You are an expert SQL developer tasked with converting natural language queries into precise SQL queries.
            
            Database Schema:
            {schema}
            
            User Question: {user_query}
            
            Remember the dates are in the format dd-mm-yyyy or mm-yyyy.
            
            Follow these steps to convert the user question into a SQL query:
            Step 1: Analyze the user question to understand what information they're looking for.
            Step 2: Identify the relevant tables and columns from the provided schema that are needed to answer the question.
            Step 3: Identify any filters, aggregations, groupings, or sorting required by the question.
            Step 4: Consider edge cases and add appropriate error handling or NULL checks if needed.
            Step 5: Write the SQL query following best practices.
            Step 6: Review the query for accuracy and efficiency.
            
            After completing all steps of your thinking, output ONLY the final SQL query without any explanation, comments, markdown formatting, or additional text. The query should be valid SQL that can be directly executed against the database.
            
            Here are some examples of natural language queries and the corresponding SQL queries:

            Example 1:
            User Question: How many transactions were entered in March 2024?
            SQL Query:
            SELECT COUNT(*) FROM transaction_score WHERE ENTERED_DATE LIKE '__-03-2024%';
            
            Example 2:
            User Question: List all transactions with AI risk score greater than 0.8, sorted by score in descending order
            SQL Query:
            SELECT * FROM transaction_score WHERE AI_RISK_SCORE > 0.8 ORDER BY AI_RISK_SCORE DESC;
            
            Example 3:
            User Question: Show me the total debit and credit amounts by month for 2023, but only include months with transactions exceeding $10,000 in total value
            SQL Query:
            SELECT 
                substr(ENTERED_DATE, 4, 2) AS Month, 
                substr(ENTERED_DATE, 7, 4) AS Year, 
                SUM(DEBIT_AMOUNT) AS Total_Debits, 
                SUM(CREDIT_AMOUNT) AS Total_Credits
            FROM transaction_score 
            WHERE substr(ENTERED_DATE, 7, 4) = '2023' 
            GROUP BY substr(ENTERED_DATE, 4, 2), substr(ENTERED_DATE, 7, 4)
            HAVING (SUM(DEBIT_AMOUNT) + SUM(CREDIT_AMOUNT)) > 10000
            ORDER BY Month;
        """
        )
    
    chain = (
            {"schema": RunnablePassthrough(), "user_query": RunnablePassthrough()}
            | chat_template
            | model
            | StrOutputParser()
        )
    query = chain.invoke({"schema": schema, "user_query": user_query})
    print("QUERY:", query)
    return query

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
            
            model = ChatOllama(model=SQL_GENERATOR_MODEL)
            rephrased_query = await rephrase_query(user_query+" in the table transaction_score")
            # response = await generate_sql(user_query, tools)
            # prompt = f"""
            #     You are an expert SQL generator and analyst.

            #     You will be given:
            #     1. A natural language query that has already been rephrased to match a known database schema.
            #     2. The database schema itself, which includes table names and column names.

            #     Your task is to:
            #     - Generate a syntactically correct SQL query based strictly on the schema.
            #     - Map values (like dates, names, scores, etc.) to the appropriate column names in the schema — do NOT guess.
            #     - Use only the exact column and table names from the schema.
            #     - Use date formats as dd-mm-yyyy or mm-yyyy.
            #     - Do not include any columns or tables that are not explicitly present in the schema.
            #     - If you cannot find a matching column, return: "Invalid: Unable to generate SQL. Missing column/table in schema."

            #     Then:
            #     - Execute the SQL query and write a **short, human-friendly answer** based on the expected output.
            #     - Do NOT explain or include the reasoning — just output the SQL and the final answer.

            #     Database Schema:
            #     {schema}
            #     Rephrased Query:
            #     {rephrased_query}

            #     Begin:"""
            
            prompt = f"""
            You are an expert SQL generator and analyst.
            Excecute the given sql query and return the response to the user in natural language without any additional comments.
             
            SQL Query:
            {rephrased_query}
            
            Answer:
            """
            agent = create_react_agent(model, tools)
            response = await agent.ainvoke({"messages": prompt})
            print("RESPONSE:", response)
            # return response
            return response['messages'][-1].content

# Main Streamlit app
async def main():
    st.set_page_config(page_title="Natural Language to SQL", page_icon="🧠")
    st.title("🧠 Natural Language to SQL with Ollama")
    st.write("Type your question in natural language and get SQL-powered answers!")

    # Initialize chat history in session state
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # Display chat messages
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            
    nl_query = st.chat_input("Ask your question about the database:")

    if nl_query:
        st.session_state.chat_history.append({"role": "user", "content": nl_query})
        with st.chat_message("user"):
            st.markdown(nl_query)
            
        try:
            with st.spinner("Running SQL query..."):
                
                result = await call_ollama(nl_query)
            # st.success("Query executed successfully!")
            
            # Show assistant response
            # response_text = "\n".join(msg.content for msg in result["messages"])
            st.session_state.chat_history.append({"role": "assistant", "content": result})
            with st.chat_message("assistant"):
                st.markdown(result)
                
            # for message in result['messages']:
            #     st.text(message.content)
        except Exception as e:
            st.error(f"Error running query: {e}")
            st.session_state.chat_history.append({"role": "assistant", "content": e})
            with st.chat_message("assistant"):
                st.error(e)
                st.code(traceback.format_exc())

# Run the app
if __name__ == "__main__":
    asyncio.run(main())
