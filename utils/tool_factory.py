"""Factory functions for creating MCP tools with reduced boilerplate."""

from typing import Callable
from fastmcp import FastMCP
from utils import TWSEAPIClient, format_properties_with_values_multiline


def create_company_tool(mcp: FastMCP, endpoint: str, name: str, docstring: str) -> Callable[[str], str]:
    """
    Create and register a standard company data query tool.
    
    Args:
        mcp: FastMCP instance
        endpoint: TWSE API endpoint (e.g., "/opendata/t187ap46_L_9")
        name: Function name for the tool
        docstring: Tool description
        
    Returns:
        The registered tool function
    """
    @mcp.tool(name=name, description=docstring)
    def tool_fn(code: str) -> str:
        try:
            data = TWSEAPIClient.get_company_data(endpoint, code)
            return format_properties_with_values_multiline(data) if data else ""
        except Exception:
            return ""
    
    return tool_fn
