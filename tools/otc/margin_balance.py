"""OTC margin balance (融資融券) from TPEx openapi."""

from typing import Optional
from fastmcp import FastMCP
from utils import TWSEAPIClient, handle_api_errors, DEFAULT_DISPLAY_LIMIT

TPEX_MARGIN_URL = "https://www.tpex.org.tw/openapi/v1/tpex_mainboard_margin_balance"


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    """Register OTC margin balance tools."""
    _client = client or TWSEAPIClient.get_instance()

    @mcp.tool
    @handle_api_errors()
    def get_otc_margin_balance(stock_no: str = "", limit: int = DEFAULT_DISPLAY_LIMIT, offset: int = 0) -> str:
        """查詢上櫃股票融資融券餘額，包含融資餘額、融券餘額、融資使用率。
        可指定股票代號只查單一個股。與上市版 get_margin_balance 對應。

        Args:
            stock_no: 股票代號（選填），若指定則只回傳該股票的融資融券資料
            limit: 回傳筆數上限（預設 50）
            offset: 跳過前 N 筆（預設 0，搭配 limit 分頁；指定 stock_no 時忽略）

        Returns:
            每支上櫃股的融資餘額、融券餘額、融資使用率等資料
        """
        data = _client.fetch_json(TPEX_MARGIN_URL)

        if not isinstance(data, list) or not data:
            return "查無上櫃市場融資融券餘額資料"

        if stock_no:
            data = [d for d in data if d.get("SecuritiesCompanyCode", "").strip() == stock_no]
            if not data:
                return f"查無上櫃股票代號 {stock_no} 的融資融券資料"

        total = len(data)
        page_data = data[offset:offset + limit]
        end = min(offset + limit, total)

        header = f"【上櫃融資融券餘額】（共 {total} 筆"
        if total > limit or offset > 0:
            header += f"，顯示第 {offset + 1}–{end} 筆"
        header += "）\n"

        lines = [header]
        for item in page_data:
            code = item.get("SecuritiesCompanyCode", "?")
            name = item.get("CompanyName", "?")
            margin_bal = item.get("MarginPurchaseBalance", "-")
            short_bal = item.get("ShortSaleBalance", "-")
            util_rate = item.get("MarginPurchaseUtilizationRate", "-")
            lines.append(
                f"{code} {name} | 融資餘額: {margin_bal} | 融券餘額: {short_bal} | 融資使用率: {util_rate}%"
            )

        remaining = total - offset - limit
        if remaining > 0 and not stock_no:
            lines.append(f"\n...還有 {remaining} 筆，使用 offset={offset + limit} 查看更多")

        return "\n".join(lines)
