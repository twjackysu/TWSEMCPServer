"""Main MCP server for Taiwan Stock Exchange data analysis."""

from fastmcp import FastMCP
from fastmcp.prompts.prompt import PromptMessage
import logging

from prompts.twse_stock_trend_prompt import twse_stock_trend_prompt
from prompts.foreign_investment_analysis_prompt import foreign_investment_analysis_prompt
from prompts.market_hotspot_monitoring_prompt import market_hotspot_monitoring_prompt
from prompts.dividend_investment_strategy_prompt import dividend_investment_strategy_prompt
from prompts.investment_screening_prompt import investment_screening_prompt
from tools import register_all_tools
from utils.api_client import TWSEAPIClient

# Configure logging (similar to .NET ILogger)
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# Initialize FastMCP server
mcp = FastMCP("TWSE Stock Trend Analysis 🚀")

# Initialize API Client
# This is the root of our Dependency Injection tree
api_client = TWSEAPIClient()

# Register prompts
@mcp.prompt
def stock_trend_analysis_prompt(stock_symbol: str, period: str) -> PromptMessage:
    """Prompt for Taiwan stock trend analysis using TWSE OpenAPI endpoints."""
    return twse_stock_trend_prompt(stock_symbol, period)

@mcp.prompt
def foreign_investment_analysis(analysis_type: str = "overview", industry: str = "", stock_symbol: str = "") -> PromptMessage:
    """Prompt for foreign investment analysis using TWSE OpenAPI endpoints."""
    return foreign_investment_analysis_prompt(analysis_type, industry, stock_symbol)

@mcp.prompt
def market_hotspot_monitoring(monitoring_scope: str = "comprehensive", date_filter: str = "today") -> PromptMessage:
    """Prompt for market hotspot monitoring using TWSE OpenAPI endpoints."""
    return market_hotspot_monitoring_prompt(monitoring_scope, date_filter)

@mcp.prompt
def dividend_investment_strategy(strategy_type: str = "high_yield", time_horizon: str = "quarterly") -> PromptMessage:
    """Prompt for dividend investment strategy using TWSE OpenAPI endpoints."""
    return dividend_investment_strategy_prompt(strategy_type, time_horizon)

@mcp.prompt
def investment_screening(screening_criteria: str = "comprehensive", risk_level: str = "moderate") -> PromptMessage:
    """Prompt for investment screening using TWSE OpenAPI endpoints."""
    return investment_screening_prompt(screening_criteria, risk_level)

# Pass dependencies to tool registration
register_all_tools(mcp, api_client)

if __name__ == "__main__":
    # Run the MCP server
    mcp.run(transport="http", host="0.0.0.0", port=8000)
