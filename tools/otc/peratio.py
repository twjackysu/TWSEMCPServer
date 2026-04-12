"""OTC valuation ratios (P/E, dividend yield, P/B) from TPEx openapi."""

from typing import Optional
from fastmcp import FastMCP
from utils import TWSEAPIClient, handle_api_errors

TPEX_PE_URL = "https://www.tpex.org.tw/openapi/v1/tpex_mainboard_peratio_analysis"


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    """Register OTC valuation tools."""
    _client = client or TWSEAPIClient.get_instance()

    @mcp.tool
    @handle_api_errors()
    def get_otc_valuation(stock_no: str = "") -> str:
        """查詢上櫃股票本益比、殖利率、股價淨值比，與上市市場估值工具對應。

        Args:
            stock_no: 股票代號（選填），若指定則只回傳該股票的估值資料

        Returns:
            每支上櫃股的本益比、殖利率(%)、股價淨值比
        """
        data = _client.fetch_json(TPEX_PE_URL)

        if not isinstance(data, list) or not data:
            return "查無上櫃市場估值資料"

        if stock_no:
            data = [d for d in data if d.get("SecuritiesCompanyCode", "").strip() == stock_no]
            if not data:
                return f"查無上櫃股票代號 {stock_no} 的估值資料"

        lines = [f"【上櫃市場估值資料】（共 {len(data)} 筆）\n"]

        for item in data[:50]:
            code = item.get("SecuritiesCompanyCode", "?")
            name = item.get("CompanyName", "?")
            pe = item.get("PriceEarningRatio", "-")
            dy = item.get("YieldRatio", item.get("DividendYield", "-"))
            pb = item.get("PriceBookRatio", "-")

            lines.append(f"{code} {name} | 本益比: {pe} | 殖利率: {dy}% | 股價淨值比: {pb}")

        if len(data) > 50 and not stock_no:
            lines.append(f"\n...還有 {len(data) - 50} 筆資料未顯示")

        return "\n".join(lines)
