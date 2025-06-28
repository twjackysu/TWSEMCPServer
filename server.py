"""Main MCP server for Taiwan Stock Exchange data analysis."""

from fastmcp import FastMCP
from fastmcp.prompts.prompt import PromptMessage
import logging

from prompts.twse_stock_trend_prompt import twse_stock_trend_prompt
from tools import register_all_tools

# Configure logging (similar to .NET ILogger)
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# Initialize FastMCP server
mcp = FastMCP("TWSE Stock Trend Analysis 🚀")

# Register prompt
@mcp.prompt
def stock_trend_analysis_prompt(stock_symbol: str, period: str) -> PromptMessage:
    """Prompt for Taiwan stock trend analysis using TWSE OpenAPI endpoints."""
    return twse_stock_trend_prompt(stock_symbol, period)

if __name__ == "__main__":
    # Register all tools before running the server
    logger.info("Registering MCP tools...")
    register_all_tools(mcp)
    logger.info("All MCP tools registered successfully!")
    
    # Run the MCP server
    mcp.run(transport='stdio')