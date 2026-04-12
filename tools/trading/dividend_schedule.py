"""Dividend and rights schedule related tools for Taiwan Stock Exchange MCP server."""

from typing import Optional
from fastmcp import FastMCP
from utils import TWSEAPIClient, format_multiple_records, format_properties_with_values_multiline, MSG_QUERY_FAILED


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    # Use injected client or fallback to singleton
    _client = client or TWSEAPIClient.get_instance()

    @mcp.tool
    def get_dividend_rights_schedule(code: str = "") -> str:
        """查詢上市股票除權除息預告表。

        Args:
            code: 股票代號（選填）。若指定則只回傳該公司的除權息資訊。
        """
        try:
            if code:
                data = _client.fetch_company_data("/exchangeReport/TWT48U_ALL", code)
                return format_properties_with_values_multiline(data) if data else ""
            else:
                data = _client.fetch_data("/exchangeReport/TWT48U_ALL")
                return format_multiple_records(data) if data else ""
        except Exception as e:
            return MSG_QUERY_FAILED.format(error=str(e))