"""Main MCP server for Taiwan Stock Exchange data analysis."""

from collections.abc import Mapping
from fastmcp import FastMCP
from fastmcp.prompts.prompt import PromptMessage
import logging
import os

from prompts.twse_stock_trend_prompt import twse_stock_trend_prompt
from prompts.foreign_investment_analysis_prompt import foreign_investment_analysis_prompt
from prompts.market_hotspot_monitoring_prompt import market_hotspot_monitoring_prompt
from prompts.dividend_investment_strategy_prompt import dividend_investment_strategy_prompt
from prompts.investment_screening_prompt import investment_screening_prompt
from prompts.taifex_derivatives_prompt import taifex_derivatives_prompt
from prompts.institutional_flow_prompt import institutional_flow_prompt
from prompts.company_fundamental_healthcheck_prompt import company_fundamental_healthcheck_prompt
from prompts.pre_trade_risk_scan_prompt import pre_trade_risk_scan_prompt
from tools import register_all_tools
from utils.api_client import TWSEAPIClient
from utils.http_auth import APIKeyTokenVerifier

# Configure logging (similar to .NET ILogger)
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)


class TWSEFastMCP(FastMCP):
    """FastMCP server that also secures HTTP runs started through the CLI."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._http_api_key_auth_configured = False

    def configure_http_auth(
        self, environ: Mapping[str, str] | None = None
    ) -> None:
        """Attach environment-managed API-key auth to HTTP transports."""
        self.auth = APIKeyTokenVerifier.from_environment(environ)
        self._http_api_key_auth_configured = True

    async def run_async(
        self, transport=None, show_banner: bool = True, **transport_kwargs
    ) -> None:
        if (
            transport in {"http", "streamable-http", "sse"}
            and not self._http_api_key_auth_configured
        ):
            self.configure_http_auth()
        await super().run_async(
            transport=transport,
            show_banner=show_banner,
            **transport_kwargs,
        )


# Initialize FastMCP server
mcp = TWSEFastMCP("TWSE Stock Trend Analysis 🚀")

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

@mcp.prompt
def taifex_derivatives(scope: str = "comprehensive") -> PromptMessage:
    """Prompt for TAIFEX futures/options chip analysis using TAIFEX OpenAPI endpoints."""
    return taifex_derivatives_prompt(scope)

@mcp.prompt
def institutional_flow(target: str = "market", stock_symbol: str = "") -> PromptMessage:
    """Prompt for three-major-institutional-investors (foreign/investment trust/dealer) flow analysis."""
    return institutional_flow_prompt(target, stock_symbol)

@mcp.prompt
def company_fundamental_healthcheck(stock_symbol: str, depth: str = "standard") -> PromptMessage:
    """Prompt for a comprehensive fundamental/financial-statement health check on a company."""
    return company_fundamental_healthcheck_prompt(stock_symbol, depth)

@mcp.prompt
def pre_trade_risk_scan(market: str = "twse", stock_symbol: str = "") -> PromptMessage:
    """Prompt for scanning disposal/warning/restriction lists before placing a trade."""
    return pre_trade_risk_scan_prompt(market, stock_symbol)

# Pass dependencies to tool registration
register_all_tools(mcp, api_client)

def run_server(environ: Mapping[str, str] | None = None) -> None:
    """Run stdio directly or configure required bearer auth before HTTP starts."""
    environment = os.environ if environ is None else environ
    if environment.get("MCP_STDIO", "").lower() in ("1", "true"):
        # docker run -i --rm -e MCP_STDIO=1 ...
        mcp.run(transport="stdio")
    else:
        mcp.configure_http_auth(environment)
        port = int(environment.get("PORT", "8000"))
        mcp.run(transport="http", host="0.0.0.0", port=port)


if __name__ == "__main__":
    run_server()
