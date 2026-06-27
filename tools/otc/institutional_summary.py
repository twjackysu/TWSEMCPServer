"""OTC institutional investors summary (三大法人彙總) from TPEx openapi."""

from typing import Optional
from fastmcp import FastMCP
from utils import TWSEAPIClient, handle_api_errors

TPEX_3INSTI_SUMMARY_URL = "https://www.tpex.org.tw/openapi/v1/tpex_3insti_summary"


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    """Register OTC institutional summary tools."""
    _client = client or TWSEAPIClient.get_instance()

    @mcp.tool
    @handle_api_errors()
    def get_otc_institutional_summary() -> str:
        """查詢上櫃市場三大法人（外資、投信、自營商）當日買賣超彙總，顯示整體市場層面的法人動向。
        與 get_otc_institutional（個股明細）互補。

        Returns:
            外資、投信、自營商各類別的買進金額、賣出金額、買賣超淨額
        """
        data = _client.fetch_json(TPEX_3INSTI_SUMMARY_URL)

        if not isinstance(data, list) or not data:
            return "查無上櫃三大法人彙總資料"

        date = data[0].get("Date", "?")
        lines = [f"【上櫃三大法人彙總】日期: {date}\n"]
        for item in data:
            investor = item.get("Investor", "?")
            buy = item.get("PurchaseAmount", "-")
            sell = item.get("SaleAmount", "-")
            net = item.get("Net", "-")
            lines.append(f"{investor} | 買進: {buy} | 賣出: {sell} | 買賣超: {net}")

        return "\n".join(lines)
