"""OTC (TPEx) market index data from TPEx openapi."""

from typing import Optional
from fastmcp import FastMCP
from utils import TWSEAPIClient, DEFAULT_DISPLAY_LIMIT, Page
from toolkit import handle_api_errors

TPEX_INDEX_URL = "https://www.tpex.org.tw/openapi/v1/tpex_index"


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    """Register OTC index tools."""
    _client = client or TWSEAPIClient.get_instance()

    @mcp.tool
    @handle_api_errors()
    def get_otc_index(limit: int = DEFAULT_DISPLAY_LIMIT, offset: int = 0) -> str:
        """查詢櫃買市場（上櫃）指數歷史行情，包含開高低收、漲跌幅。

        回傳：櫃買指數各期日期、開盤、最高、最低、收盤、漲跌

        Args:
            limit: 回傳筆數上限（預設 50）
            offset: 跳過前 N 筆（預設 0，搭配 limit 分頁）
        """
        data = _client.fetch_json(TPEX_INDEX_URL)

        if not isinstance(data, list) or not data:
            return "查無櫃買指數資料"

        paged = Page(limit, offset).take(data)
        if paged.past_end:
            return paged.out_of_range("櫃買指數資料")

        header = f"【櫃買市場指數】（共 {paged.total} 筆"
        if paged.span():
            header += f"，{paged.span()}"
        header += "）\n"

        lines = [header]
        for item in paged.rows:
            date = item.get("Date", "?")
            open_p = item.get("Open", "-")
            high = item.get("High", "-")
            low = item.get("Low", "-")
            close = item.get("Close", "-")
            change = item.get("Change", "-")
            lines.append(f"{date} | 開: {open_p} | 高: {high} | 低: {low} | 收: {close} | 漲跌: {change}")

        if paged.more():
            lines.append("\n" + paged.more())

        return "\n".join(lines)
