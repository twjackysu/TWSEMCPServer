"""Factory functions for creating MCP tools with reduced boilerplate."""

from typing import Callable, Optional
from fastmcp import FastMCP
from utils import TWSEAPIClient, format_properties_with_values_multiline
from utils.decorators import handle_api_errors

def create_company_tool(mcp: FastMCP, endpoint: str, name: str, docstring: str, client: Optional[TWSEAPIClient] = None) -> Callable[[str], str]:
    """
    Create and register a standard company data query tool.

    Args:
        mcp: FastMCP instance
        endpoint: TWSE API endpoint (e.g., "/opendata/t187ap46_L_9")
        name: Function name for the tool
        docstring: Tool description
        client: TWSEAPIClient instance for dependency injection

    Returns:
        The registered tool function
    """
    _client = client or TWSEAPIClient.get_instance()

    def tool_fn(code: str) -> str:
        data = _client.fetch_company_data(endpoint, code)
        return format_properties_with_values_multiline(data) if data else ""

    tool_fn.__name__ = name
    decorated = handle_api_errors(use_code_param=True)(tool_fn)
    mcp.tool(name=name, description=docstring)(decorated)
    return decorated
