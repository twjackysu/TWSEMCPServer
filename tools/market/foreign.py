"""Foreign investment related tools for Taiwan Stock Exchange MCP server."""

from typing import Optional
from fastmcp import FastMCP
from utils import TWSEAPIClient, handle_api_errors, format_multiple_records


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    # Use injected client or fallback to singleton
    _client = client or TWSEAPIClient.get_instance()

    @mcp.tool
    @handle_api_errors()
    def get_foreign_investment_by_industry() -> str:
        """查詢集中市場外資及陸資投資類股持股比率表（最新一日，產業別匯總）。
        個股外資持股與持股排行請用 get_foreign_holdings。

        回傳各產業的公司家數、總發行股數、外資持有股數及持股比率。
        """
        data = _client.fetch_data("/fund/MI_QFIIS_cat")
        return format_multiple_records(data) if data else ""
