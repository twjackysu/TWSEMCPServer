"""OTC institutional (三大法人) trading data from TPEx openapi."""

from typing import Optional
from fastmcp import FastMCP
from utils import TWSEAPIClient, handle_api_errors

TPEX_3INSTI_URL = "https://www.tpex.org.tw/openapi/v1/tpex_3insti_daily_trading"


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    """Register OTC institutional trading tools."""
    _client = client or TWSEAPIClient.get_instance()

    @mcp.tool
    @handle_api_errors()
    def get_otc_institutional(stock_no: str = "") -> str:
        """查詢上櫃市場三大法人（外資、投信、自營商）每日買賣超資料。
        可指定特定股票代號只查單一個股。

        Args:
            stock_no: 股票代號（選填），若指定則只回傳該股票的法人買賣超

        Returns:
            每支上櫃股的外資/投信/自營商買進、賣出、買賣超資料
        """
        data = _client.fetch_json(TPEX_3INSTI_URL)

        if not isinstance(data, list) or not data:
            return "查無上櫃市場三大法人買賣超資料"

        if stock_no:
            data = [d for d in data if d.get("SecuritiesCompanyCode", "").strip() == stock_no]
            if not data:
                return f"查無上櫃股票代號 {stock_no} 的三大法人資料"

        # Field name keys from API (very long English names)
        FK_BUY = "ForeignInvestorsIncludeMainlandAreaInvestors-TotalBuy"
        FK_SELL = "ForeignInvestorsIncludeMainlandAreaInvestors-TotalSell"
        FK_NET = "ForeignInvestorsInclude MainlandAreaInvestors-Difference"
        IT_BUY = "SecuritiesInvestmentTrustCompanies-TotalBuy"
        IT_SELL = "SecuritiesInvestmentTrustCompanies-TotalSell"
        IT_NET = "SecuritiesInvestmentTrustCompanies-Difference"
        DL_BUY = "Dealers-TotalBuy"
        DL_SELL = "Dealers-TotalSell"
        DL_NET = "Dealers-Difference"
        TOTAL_NET = "TotalDifference"

        lines = [f"【上櫃三大法人買賣超】（共 {len(data)} 筆）\n"]

        for item in data[:50]:
            code = item.get("SecuritiesCompanyCode", "?")
            name = item.get("CompanyName", "?")
            fk_net = item.get(FK_NET, "-")
            it_net = item.get(IT_NET, "-")
            dl_net = item.get(DL_NET, "-")
            total = item.get(TOTAL_NET, "-")

            lines.append(
                f"{code} {name} | 外資: {fk_net} | 投信: {it_net} | "
                f"自營: {dl_net} | 合計: {total}"
            )

        if len(data) > 50 and not stock_no:
            lines.append(f"\n...還有 {len(data) - 50} 筆資料未顯示")

        return "\n".join(lines)
