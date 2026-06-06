"""ETF related tools for Taiwan Stock Exchange MCP server."""

from typing import Optional
from fastmcp import FastMCP
from utils import TWSEAPIClient, handle_api_errors, format_multiple_records


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    # Use injected client or fallback to singleton
    _client = client or TWSEAPIClient.get_instance()

    @mcp.tool
    @handle_api_errors()
    def get_etf_regular_investment_ranking() -> str:
        """查詢定期定額交易戶數統計排行月報表。"""
        data = _client.fetch_data("/ETFReport/ETFRank")
        return format_multiple_records(data) if data else ""
