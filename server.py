"""Main MCP server for Taiwan Stock Exchange data analysis."""

from fastmcp import FastMCP
import logging

from prompts.twse_stock_trend_prompt import twse_stock_trend_prompt
from prompts.foreign_investment_analysis_prompt import foreign_investment_analysis_prompt
from prompts.market_hotspot_monitoring_prompt import market_hotspot_monitoring_prompt
from prompts.dividend_investment_strategy_prompt import dividend_investment_strategy_prompt
from prompts.investment_screening_prompt import investment_screening_prompt
from prompts.taifex_derivatives_prompt import taifex_derivatives_prompt
from prompts.institutional_flow_prompt import institutional_flow_prompt
from prompts.company_fundamental_healthcheck_prompt import company_fundamental_healthcheck_prompt
from prompts.pre_trade_risk_scan_prompt import pre_trade_risk_scan_prompt
from toolkit import ArgumentErrorsInChinese
from tools import SOURCES, enabled_sources, register_all_tools, show_only_sources
from utils.api_client import TWSEAPIClient
from utils.config import ServerConfig

# Configure logging (similar to .NET ILogger)
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# The data sources this deployment serves (TWSE_INCLUDE_SOURCES / TWSE_EXCLUDE_SOURCES; default all).
SERVED_SOURCES = enabled_sources(ServerConfig.INCLUDE_SOURCES, ServerConfig.EXCLUDE_SOURCES)

# Sent once to every client at initialization (MCP `instructions`), so the date convention that holds
# for all tools is not repeated in 177 tool descriptions. Replies keep the sources' ROC (民國) dates.
SERVER_INSTRUCTIONS = f"""台灣證券市場資料：{'、'.join(name for tag, name in SOURCES.items() if tag in SERVED_SOURCES)}。

日期慣例：
- 工具的日期參數（date、start_date、end_date）一律是西元 YYYYMMDD，例如 20260930；月份參數（YYYYMM）也是西元。
- 回覆中的日期常沿用資料來源的民國紀年，民國年 + 1911 = 西元年：115/09/30、115年09月30日、1150930 都是 2026-09-30，115年09月 是 2026 年 9 月。
- 財報期別 115/2、115Q2 是 2026 年第 2 季；股利年度 114 是 2025 年。
- 拿回覆中的民國日期再查詢時，先換算成西元，例如 1150930 → 20260930。
- 少數參數是「年度」而不是日期（例如公開資訊觀測站財報、股利、重大訊息的 year），西元或民國皆可，以各參數說明為準。"""

# Initialize FastMCP server
mcp = FastMCP("TWSE Stock Trend Analysis 🚀", instructions=SERVER_INSTRUCTIONS)
# FastMCP rejects arguments outside a tool's schema (toolkit/params.py); say why in Chinese.
mcp.add_middleware(ArgumentErrorsInChinese())

# Initialize API Client
# This is the root of our Dependency Injection tree
api_client = TWSEAPIClient()

# Register prompts. Each prompt's tags are the sources of the tools it names (checked by
# tests/unit/test_source_visibility_unit.py); it stays visible while any of them is served.
@mcp.prompt(tags={"twse", "tpex", "mops", "tdcc", "ndc", "cbc"})
def stock_trend_analysis_prompt(stock_symbol: str, period: str) -> str:
    """Prompt for Taiwan stock trend analysis using TWSE OpenAPI endpoints."""
    return twse_stock_trend_prompt(stock_symbol, period)

@mcp.prompt(tags={"twse", "tpex", "mops", "tdcc", "cbc"})
def foreign_investment_analysis(analysis_type: str = "overview", industry: str = "", stock_symbol: str = "") -> str:
    """Prompt for foreign investment analysis using TWSE OpenAPI endpoints."""
    return foreign_investment_analysis_prompt(analysis_type, industry, stock_symbol)

@mcp.prompt(tags={"twse", "mops", "sitca", "ndc", "cbc"})
def market_hotspot_monitoring(monitoring_scope: str = "comprehensive", date_filter: str = "today") -> str:
    """Prompt for market hotspot monitoring using TWSE OpenAPI endpoints."""
    return market_hotspot_monitoring_prompt(monitoring_scope, date_filter)

@mcp.prompt(tags={"twse", "tpex", "mops", "sitca"})
def dividend_investment_strategy(strategy_type: str = "high_yield", time_horizon: str = "quarterly") -> str:
    """Prompt for dividend investment strategy using TWSE OpenAPI endpoints."""
    return dividend_investment_strategy_prompt(strategy_type, time_horizon)

@mcp.prompt(tags={"twse", "tpex", "mops", "tdcc", "sitca", "ndc"})
def investment_screening(screening_criteria: str = "comprehensive", risk_level: str = "moderate") -> str:
    """Prompt for investment screening using TWSE OpenAPI endpoints."""
    return investment_screening_prompt(screening_criteria, risk_level)

@mcp.prompt(tags={"taifex"})
def taifex_derivatives(scope: str = "comprehensive") -> str:
    """Prompt for TAIFEX futures/options chip analysis using TAIFEX OpenAPI endpoints."""
    return taifex_derivatives_prompt(scope)

@mcp.prompt(tags={"twse", "tpex", "taifex", "mops", "tdcc"})
def institutional_flow(target: str = "market", stock_symbol: str = "") -> str:
    """Prompt for three-major-institutional-investors (foreign/investment trust/dealer) flow analysis."""
    return institutional_flow_prompt(target, stock_symbol)

@mcp.prompt(tags={"twse", "tpex", "mops", "tdcc"})
def company_fundamental_healthcheck(stock_symbol: str, depth: str = "standard") -> str:
    """Prompt for a comprehensive fundamental/financial-statement health check on a company."""
    return company_fundamental_healthcheck_prompt(stock_symbol, depth)

@mcp.prompt(tags={"twse", "tpex", "mops"})
def pre_trade_risk_scan(market: str = "twse", stock_symbol: str = "") -> str:
    """Prompt for scanning disposal/warning/restriction lists before placing a trade."""
    return pre_trade_risk_scan_prompt(market, stock_symbol)

# Pass dependencies to tool registration
register_all_tools(mcp, api_client)
# Hide tools (and prompts) of the sources this deployment does not serve (FastMCP Visibility on tags).
show_only_sources(mcp, SERVED_SOURCES)

if __name__ == "__main__":
    import os
    port = int(os.getenv("PORT", "8000"))
    if os.getenv("MCP_STDIO", "").lower() in ("1", "true"):
        # docker run -i --rm -e MCP_STDIO=1 ...
        mcp.run(transport="stdio")
    else:
        mcp.run(transport="http", host="0.0.0.0", port=port)
