"""OTC ex-rights / ex-dividend daily data from TPEx openapi."""

from typing import Optional
from fastmcp import FastMCP
from utils import TWSEAPIClient, handle_api_errors, DEFAULT_DISPLAY_LIMIT

TPEX_EXRIGHT_URL = "https://www.tpex.org.tw/openapi/v1/tpex_exright_daily"


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    """Register OTC ex-rights/dividends tools."""
    _client = client or TWSEAPIClient.get_instance()

    @mcp.tool
    @handle_api_errors()
    def get_otc_exright(stock_no: str = "") -> str:
        """查詢今日上櫃除權息股票，包含除權息基準價、股票股利、現金股利。
        可指定股票代號查詢特定股票。

        Args:
            stock_no: 股票代號（選填），若指定則只回傳該股票資料

        Returns:
            除權息股票代號、名稱、除權息前收盤、除權息參考價、股票股利、現金股利、類型
        """
        data = _client.fetch_json(TPEX_EXRIGHT_URL)

        if not isinstance(data, list) or not data:
            return "今日無上櫃除權息股票資料"

        if stock_no:
            data = [d for d in data if d.get("SecuritiesCompanyCode", "").strip() == stock_no]
            if not data:
                return f"上櫃股票代號 {stock_no} 今日無除權息"

        lines = [f"【上櫃今日除權息】（共 {len(data)} 筆）\n"]
        for item in data:
            code = item.get("SecuritiesCompanyCode", "?")
            name = item.get("CompanyName", "?")
            before = item.get("ClosePriceBeforeExRightsDiviend", "-")
            ref = item.get("ExRightsDiviendQuote", "-")
            stock_div = item.get("StockDividend", "-")
            cash_div = item.get("CashDividend", "-")
            ex_type = item.get("ExRightsDiviend", "-")
            lines.append(
                f"{code} {name} | 類型: {ex_type} | 前收: {before} | 參考價: {ref} "
                f"| 股利: {stock_div} | 現金: {cash_div}"
            )

        return "\n".join(lines)
