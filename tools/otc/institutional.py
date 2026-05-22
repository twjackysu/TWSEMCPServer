"""OTC institutional (三大法人) trading data from TPEx openapi."""

from typing import Optional
from fastmcp import FastMCP
from utils import TWSEAPIClient, handle_api_errors

TPEX_3INSTI_URL = "https://www.tpex.org.tw/openapi/v1/tpex_3insti_daily_trading"

# TPEx API field name constants (very long English names from API)
FK_NET = "ForeignInvestorsInclude MainlandAreaInvestors-Difference"
IT_NET = "SecuritiesInvestmentTrustCompanies-Difference"
DL_NET = "Dealers-Difference"
TOTAL_NET = "TotalDifference"


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    """Register OTC institutional trading tools."""
    _client = client or TWSEAPIClient.get_instance()

    @mcp.tool
    @handle_api_errors()
    def get_otc_institutional(stock_no: str = "", limit: int = 50, offset: int = 0) -> str:
        """查詢上櫃市場三大法人（外資、投信、自營商）每日買賣超資料。
        可指定特定股票代號只查單一個股。

        Args:
            stock_no: 股票代號（選填），若指定則只回傳該股票的法人買賣超
            limit: 回傳筆數上限（預設 50）
            offset: 跳過前 N 筆（預設 0，搭配 limit 分頁；指定 stock_no 時忽略）

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

        total = len(data)
        page_data = data[offset:offset + limit]
        end = min(offset + limit, total)

        header = f"【上櫃三大法人買賣超】（共 {total} 筆"
        if total > limit or offset > 0:
            header += f"，顯示第 {offset + 1}–{end} 筆"
        header += "）\n"

        lines = [header]
        for item in page_data:
            code = item.get("SecuritiesCompanyCode", "?")
            name = item.get("CompanyName", "?")
            fk_net = item.get(FK_NET, "-")
            it_net = item.get(IT_NET, "-")
            dl_net = item.get(DL_NET, "-")
            total_net = item.get(TOTAL_NET, "-")
            lines.append(
                f"{code} {name} | 外資: {fk_net} | 投信: {it_net} | "
                f"自營: {dl_net} | 合計: {total_net}"
            )

        remaining = total - offset - limit
        if remaining > 0 and not stock_no:
            lines.append(f"\n...還有 {remaining} 筆，使用 offset={offset + limit} 查看更多")

        return "\n".join(lines)
