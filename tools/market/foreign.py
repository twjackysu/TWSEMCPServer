"""Foreign investment related tools for Taiwan Stock Exchange MCP server."""

from typing import Optional
from fastmcp import FastMCP
from utils import TWSEAPIClient, format_multiple_records, MSG_QUERY_FAILED


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    # Use injected client or fallback to singleton
    _client = client or TWSEAPIClient.get_instance()

    @mcp.tool
    def get_foreign_investment_by_industry() -> str:
        """查詢集中市場外資及陸資投資類股持股比率表。

        回傳各產業的公司家數、總發行股數、外資持有股數及持股比率。
        """
        try:
            data = _client.fetch_data("/fund/MI_QFIIS_cat")
            return format_multiple_records(data) if data else ""
        except Exception as e:
            return MSG_QUERY_FAILED.format(error=str(e))

    @mcp.tool  
    def get_top_foreign_holdings() -> str:
        """查詢集中市場外資及陸資持股前20名彙總表。

        回傳外資持股最高的公司排名，包含投資上限、持有股數及可投資餘額。
        """
        try:
            data = _client.fetch_data("/fund/MI_QFIIS_sort_20")
            return format_multiple_records(data) if data else ""
        except Exception as e:
            return MSG_QUERY_FAILED.format(error=str(e))