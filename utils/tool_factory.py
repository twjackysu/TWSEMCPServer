"""Factory functions for creating MCP tools with reduced boilerplate."""

from typing import Callable, Optional
from fastmcp import FastMCP
from utils import TWSEAPIClient, format_properties_with_values_multiline
import logging

logger = logging.getLogger(__name__)

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
    logger.info(f"Creating dynamic tool: {name}")
    
    # Use injected client or fallback to singleton
    _client = client or TWSEAPIClient.get_instance()
    
    def tool_fn(code: str) -> str:
        try:
            # Use instance method for data fetching
            data = _client.fetch_company_data(endpoint, code)
            return format_properties_with_values_multiline(data) if data else ""
        except Exception as e:
            logger.error(f"Error in dynamic tool {name}: {e}")
            return ""
            
    # Explicitly set function name to match tool name
    # This prevents FastMCP from overwriting tools if it keys off __name__
    tool_fn.__name__ = name
    
    # Apply decorator manually
    mcp.tool(name=name, description=docstring)(tool_fn)
    
    return tool_fn
