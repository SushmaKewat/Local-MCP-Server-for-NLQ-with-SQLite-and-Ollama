from mcp.server.fastmcp import FastMCP
from mcp.shared.exceptions import McpError
from mcp.types import ErrorData, INVALID_PARAMS
# from mcp.server.sse import SseServerTransport

# import uvicorn
# from starlette.applications import Starlette
# from starlette.requests import Request
# from starlette.routing import Route, Mount

import sqlite3


mcp = FastMCP("Database Connector")

@mcp.tool()
def get_schema() -> str:
    "Get the database schema"
    conn = sqlite3.connect("SCORES.db")
    try:
        result = conn.execute("SELECT sql FROM sqlite_schema WHERE type='table'").fetchall()
        print(result)
        return "\n".join([str(row) for row in result])
    except Exception as e:
        return f"Error: {str(e)}"
    finally:
        conn.close()

@mcp.tool()
def query_data(query: str) -> str:
    "Execute read-only sql queries"
    conn = sqlite3.connect("SCORES.db")
    try:
        result = conn.execute(query).fetchall()
        conn.commit()
        print(result)
        return "\n".join([str(row) for row in result])
    except ValueError as e:
        raise McpError(ErrorData(INVALID_PARAMS, str(e))) from e
    except Exception as e:
        return f"Error: {str(e)}"
    finally:
        conn.close()
        
# sse = SseServerTransport('/messages')

# async def handle_sse(request: Request) -> None:
#     _server = mcp._mcp_server
#     async with sse.connect_sse(
#         request.scope,
#         request.receive,
#         request._send,  # type: ignore[reportPrivateUsage]
#     ) as (reader, writer):
#         await _server.run(
#             reader,
#             writer,
#             _server.create_initialization_options()
#         )
    
    
# app = Starlette(routes=[
#     Route("/sse", endpoint=handle_sse),
#     Mount('/messages/', app=sse.handle_post_message),
# ])

if __name__ == "__main__":
    # uvicorn.run(app, host="localhost", port=8000)
    mcp.run(transport="stdio")