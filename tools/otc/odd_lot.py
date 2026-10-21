"""OTC odd-lot (零股) trading data from TPEx openapi."""

from typing import Optional
from fastmcp import FastMCP
from utils import TWSEAPIClient, DEFAULT_DISPLAY_LIMIT, Page
from toolkit import handle_api_errors

TPEX_ODD_LOT_URL = "https://www.tpex.org.tw/openapi/v1/tpex_odd_stock"


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    """Register OTC odd-lot trading tools."""
    _client = client or TWSEAPIClient.get_instance()

    @mcp.tool
    @handle_api_errors()
    def get_otc_odd_lot(stock_no: str = "", limit: int = DEFAULT_DISPLAY_LIMIT, offset: int = 0) -> str:
        """查詢上櫃零股（不足一張）交易行情，包含零股成交價、成交量、成交金額。
        可指定股票代號只查單一個股。

        回傳：每支上櫃股的零股成交價、成交股數、成交金額、最佳買/賣價

        Args:
            stock_no: 股票代號（選填），若指定則只回傳該股票的零股資料
            limit: 回傳筆數上限（預設 50）
            offset: 跳過前 N 筆（預設 0，搭配 limit 分頁；指定 stock_no 時忽略）
        """
        data = _client.fetch_json(TPEX_ODD_LOT_URL)

        if not isinstance(data, list) or not data:
            return "查無上櫃零股交易資料"

        if stock_no:
            data = [d for d in data if d.get("SecuritiesCompanyCode", "").strip() == stock_no]
            if not data:
                return f"查無上櫃股票代號 {stock_no} 的零股交易資料"

        paged = Page(limit, offset).take(data)
        if paged.past_end:
            return paged.out_of_range("上櫃零股交易資料")

        header = f"【上櫃零股交易行情】（共 {paged.total} 筆"
        if paged.span():
            header += f"，{paged.span()}"
        header += "）\n"

        lines = [header]
        for item in paged.rows:
            code = item.get("SecuritiesCompanyCode", "?")
            name = item.get("CompanyName", "?")
            price = item.get("Price", "-")
            volume = item.get("TradeVolume", "-")
            amount = item.get("TradeAmount", "-")
            lines.append(f"{code} {name} | 價: {price} | 股數: {volume} | 金額: {amount}")

        if paged.more() and not stock_no:
            lines.append("\n" + paged.more())

        return "\n".join(lines)
