"""Warrants related tools for Taiwan Stock Exchange MCP server."""

from typing import Optional
from fastmcp import FastMCP
from utils import TWSEAPIClient, handle_api_errors, format_multiple_records, format_properties_with_values_multiline


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    # Use injected client or fallback to singleton
    _client = client or TWSEAPIClient.get_instance()

    @mcp.tool
    @handle_api_errors()
    def get_warrant_basic_info(code: str = "") -> str:
        """查詢上市權證基本資料彙總表。

        Args:
            code: 權證代號（選填）。若指定則只回傳該權證資料。
        """
        if code:
            data = _client.fetch_company_data("/opendata/t187ap37_L", code)
            return format_properties_with_values_multiline(data) if data else ""
        else:
            data = _client.fetch_data("/opendata/t187ap37_L") 
            return format_multiple_records(data) if data else ""

    @mcp.tool
    @handle_api_errors()
    def get_warrant_daily_trading(code: str = "") -> str:
        """查詢上市認購(售)權證每日成交資料檔。

        Args:
            code: 權證代號（選填）。若指定則只回傳該權證成交資料。
        """
        if code:
            data = _client.fetch_company_data("/opendata/t187ap42_L", code)
            return format_properties_with_values_multiline(data) if data else ""
        else:
            data = _client.fetch_data("/opendata/t187ap42_L")
            return format_multiple_records(data) if data else ""

    @mcp.tool
    @handle_api_errors()
    def get_warrant_trader_count() -> str:
        """查詢上市認購(售)權證交易人數檔。"""
        data = _client.fetch_data("/opendata/t187ap43_L")
        return format_multiple_records(data) if data else ""

    @mcp.tool
    @handle_api_errors()
    def get_warrant_yearly_issuance_statistics() -> str:
        """查詢上市認購(售)權證年度發行量概況統計表。"""
        data = _client.fetch_data("/opendata/t187ap36_L")
        return format_multiple_records(data) if data else ""
