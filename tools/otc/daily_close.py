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
    def get_otc_daily(stock_no: str = "", limit: int = 50, offset: int = 0) -> str:
        """查詢上櫃（OTC）市場當日所有股票收盤行情。
        涵蓋台灣約 900 支上櫃股票。可指定特定股票代號只查單一個股。

        Args:
            stock_no: 股票代號（選填），若指定則只回傳該股票的收盤行情
            limit: 回傳筆數上限（預設 50）
            offset: 跳過前 N 筆（預設 0，搭配 limit 分頁；指定 stock_no 時忽略）

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

        total = len(data)
        page_data = data[offset:offset + limit]
        end = min(offset + limit, total)

        header = f"【上櫃市場收盤行情】（共 {total} 筆"
        if total > limit or offset > 0:
            header += f"，顯示第 {offset + 1}–{end} 筆"
        header += "）\n"

        lines = [header]
        for item in page_data:
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

        remaining = total - offset - limit
        if remaining > 0 and not stock_no:
            lines.append(f"\n...還有 {remaining} 筆，使用 offset={offset + limit} 查看更多")

        return "\n".join(lines)
