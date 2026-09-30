"""Per-stock daily closes and monthly average close (日收盤價及月平均收盤價), any month.

Replaces the OpenAPI /exchangeReport/STOCK_DAY_AVG_ALL tool: per stock it only gave the
latest close and this month's average, which on 2026-09-29 equalled this endpoint's
月平均收盤價 row; this endpoint also lists every day's close and accepts past months.
"""

from typing import Optional
from fastmcp import FastMCP
from utils import TWSEAPIClient, handle_api_errors, roc_to_ad

STOCK_DAY_AVG_URL = "https://www.twse.com.tw/exchangeReport/STOCK_DAY_AVG"


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    """Register stock monthly average tools."""
    _client = client or TWSEAPIClient.get_instance()

    @mcp.tool
    @handle_api_errors()
    def get_stock_monthly_average(stock_no: str, date: str = "") -> str:
        """查詢上市個股當月每日收盤價及月平均收盤價：預設本月，也可查任意過去月份，適合評估月線趨勢。

        Args:
            stock_no: 股票代號，例如 "2330"
            date: 查詢月份 YYYYMMDD（日期隨意，例如 "20250101" 查 2025 年 1 月；留空＝本月）

        Returns:
            該月份每個交易日的收盤價，以及月平均收盤價
        """
        params = {"response": "json", "stockNo": stock_no}
        if date:
            params["date"] = date
        resp = _client.fetch_json(STOCK_DAY_AVG_URL, params=params)
        date = date or (resp or {}).get("date") or "本月"

        if not resp or resp.get("stat") != "OK":
            return f"查無 {stock_no} 在 {date} 的月均價資料，請確認該日期為交易日（非假日或週末）"

        data = resp.get("data", [])
        if not data:
            return f"查無 {stock_no} 在 {date[:6]} 的月均價資料"

        title = resp.get("title", f"{stock_no} 月均價")
        lines = [f"【{title}】\n"]

        for row in data:
            # row: [日期, 收盤價]
            # Last row may be a summary (e.g. "月平均收盤價") — not a date
            if "/" not in row[0]:
                lines.append(f"{row[0]}: {row[1] if len(row) > 1 else 'N/A'}")
                continue
            ad_date = roc_to_ad(row[0])
            close = row[1] if len(row) > 1 else "N/A"
            lines.append(f"日期: {ad_date} | 收盤價: {close}")

        return "\n".join(lines)
