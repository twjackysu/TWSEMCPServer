"""Dividend and rights schedule related tools for Taiwan Stock Exchange MCP server."""

from typing import Optional
from fastmcp import FastMCP
from utils import TWSEAPIClient, handle_api_errors, format_multiple_records, format_properties_with_values_multiline


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    # Use injected client or fallback to singleton
    _client = client or TWSEAPIClient.get_instance()

    @mcp.tool
    @handle_api_errors()
    def get_dividend_rights_schedule(code: str = "") -> str:
        """查詢上市股票除權除息預告表。

        Args:
            code: 股票代號（選填）。若指定則只回傳該公司的除權息資訊。
        """
        if code:
            data = _client.fetch_company_data("/exchangeReport/TWT48U_ALL", code)
            return format_properties_with_values_multiline(data) if data else ""
        else:
            data = _client.fetch_data("/exchangeReport/TWT48U_ALL")
            return format_multiple_records(data) if data else ""
