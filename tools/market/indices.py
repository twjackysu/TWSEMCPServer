"""Market index history tools (TWSE OpenAPI indicesReport). Daily closes of every index,
incl. sector indices, are served by get_market_index_info in
tools/history/exright_day_trading_indices.py."""

from typing import Optional
from fastmcp import FastMCP
from utils import TWSEAPIClient, handle_api_errors, format_multiple_records

def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    """Register market indices tools with the MCP instance."""
    
    # Use injected client or fallback to singleton
    _client = client or TWSEAPIClient.get_instance()
    
    @mcp.tool
    @handle_api_errors()
    def get_taiwan_island_index_history() -> str:
        """查詢寶島股價指數歷史資料。"""
        data = _client.fetch_latest_market_data("/indicesReport/FRMSA", count=20)
        return format_multiple_records(data)

    @mcp.tool
    @handle_api_errors()
    def get_taiwan_50_index_history() -> str:
        """查詢臺灣50指數歷史資料。"""
        data = _client.fetch_latest_market_data("/indicesReport/TAI50I", count=20)
        return format_multiple_records(data)

    @mcp.tool
    @handle_api_errors()
    def get_taiwan_total_return_index() -> str:
        """查詢發行量加權股價報酬指數。"""
        data = _client.fetch_latest_market_data("/indicesReport/MFI94U", count=20)
        return format_multiple_records(data)
