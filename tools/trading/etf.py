"""ETF related tools for Taiwan Stock Exchange MCP server."""

from typing import Optional
from fastmcp import FastMCP
from utils import TWSEAPIClient, format_multiple_records, MSG_QUERY_FAILED


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    # Use injected client or fallback to singleton
    _client = client or TWSEAPIClient.get_instance()

    @mcp.tool
    def get_etf_regular_investment_ranking() -> str:
        """查詢定期定額交易戶數統計排行月報表。"""
        try:
            data = _client.fetch_data("/ETFReport/ETFRank")
            return format_multiple_records(data) if data else ""
        except Exception as e:
            return MSG_QUERY_FAILED.format(error=str(e))