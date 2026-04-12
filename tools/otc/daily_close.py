"""OTC daily close quotes from TPEx openapi."""

from typing import Optional
from fastmcp import FastMCP
from utils import TWSEAPIClient, handle_api_errors

TPEX_DAILY_CLOSE_URL = "https://www.tpex.org.tw/openapi/v1/tpex_mainboard_daily_close_quotes"


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    """Register OTC daily close tools."""
    _client = client or TWSEAPIClient.get_instance()

    @mcp.tool
    @handle_api_errors()
    def get_otc_daily(stock_no: str = "") -> str:
        """查詢上櫃（OTC）市場當日所有股票收盤行情。
        涵蓋台灣約 900 支上櫃股票。可指定特定股票代號只查單一個股。

        Args:
            stock_no: 股票代號（選填），若指定則只回傳該股票的收盤行情

        Returns:
            每支上櫃股的收盤價、漲跌、開盤、最高、最低、成交量等資料
        """
        data = _client.fetch_json(TPEX_DAILY_CLOSE_URL)

        if not isinstance(data, list) or not data:
            return "查無上櫃市場收盤行情資料"

        if stock_no:
            data = [d for d in data if d.get("SecuritiesCompanyCode", "").strip() == stock_no]
            if not data:
                return f"查無上櫃股票代號 {stock_no} 的收盤行情"

        lines = [f"【上櫃市場收盤行情】（共 {len(data)} 筆）\n"]

        for item in data[:50]:  # Limit output
            code = item.get("SecuritiesCompanyCode", "?")
            name = item.get("CompanyName", "?")
            close = item.get("Close", "-")
            change = item.get("Change", "-")
            open_p = item.get("Open", "-")
            high = item.get("High", "-")
            low = item.get("Low", "-")
            volume = item.get("TradingShares", "-")

            lines.append(
                f"{code} {name} | 收: {close} | 漲跌: {change} | "
                f"開: {open_p} | 高: {high} | 低: {low} | 量: {volume}"
            )

        if len(data) > 50 and not stock_no:
            lines.append(f"\n...還有 {len(data) - 50} 筆資料未顯示")

        return "\n".join(lines)
