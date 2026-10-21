"""Building blocks for tool modules: the MCP side of the server.

``utils/`` holds the data side (HTTP client, parsing, formatting) and never imports fastmcp;
everything that knows about MCP tools — the error boundary and the tool specs/factories — is here.
"""

from .decorators import handle_api_errors
from .factory import CompanyToolSpec, ListToolSpec, create_company_tool, create_list_tool

__all__ = [
    "handle_api_errors",
    "CompanyToolSpec",
    "ListToolSpec",
    "create_company_tool",
    "create_list_tool",
]
