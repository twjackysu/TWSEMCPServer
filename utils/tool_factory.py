"""Factory functions for creating MCP tools with reduced boilerplate."""

from typing import Callable
from utils import TWSEAPIClient, format_properties_with_values_multiline


def create_company_tool(mcp, endpoint: str, name: str, docstring: str) -> Callable:
    """
    Create a standard company data query tool.
    
    Args:
        mcp: FastMCP instance
        endpoint: TWSE API endpoint (e.g., "/opendata/t187ap46_L_9")
        name: Function name for the tool
        docstring: Tool description
    
    Returns:
        The registered tool function
    """
    def tool_fn(code: str) -> str:
        try:
            data = TWSEAPIClient.get_company_data(endpoint, code)
            return format_properties_with_values_multiline(data) if data else ""
        except Exception:
            return ""
    
    tool_fn.__name__ = name
    tool_fn.__doc__ = docstring
    
    return mcp.tool(tool_fn)
