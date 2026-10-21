"""Building blocks for tool modules: the MCP side of the server.

``utils/`` holds the data side (HTTP client, parsing, formatting) and never imports fastmcp;
everything that knows about MCP tools — the error boundary and the tool specs/factories — is here.
"""

from .decorators import handle_api_errors
from .factory import CompanyToolSpec, ListToolSpec, create_company_tool, create_list_tool
from .params import Limit, Offset, RequiredTradingDate, TradingDate, bounded
from .response_limit import response_limit
from .structured import output_schema, structured_reply
from .validation import ArgumentErrorsInChinese

__all__ = [
    "handle_api_errors",
    "Limit",
    "Offset",
    "bounded",
    "TradingDate",
    "RequiredTradingDate",
    "ArgumentErrorsInChinese",
    "response_limit",
    "output_schema",
    "structured_reply",
    "CompanyToolSpec",
    "ListToolSpec",
    "create_company_tool",
    "create_list_tool",
]
