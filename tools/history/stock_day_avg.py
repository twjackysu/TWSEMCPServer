"""Historical monthly average price data for individual stocks."""

from typing import Optional
from fastmcp import FastMCP
from utils import TWSEAPIClient, handle_api_errors, roc_to_ad

STOCK_DAY_AVG_URL = "https://www.twse.com.tw/exchangeReport/STOCK_DAY_AVG"


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    """Register stock monthly average tools."""
    _client = client or TWSEAPIClient.get_instance()

    @mcp.tool
    @handle_api_errors()
    def get_stock_monthly_avg_history(stock_no: str, date: str) -> str:
        """查詢個股每月均價，適合快速評估月線趨勢。

        Args:
            stock_no: 股票代號，例如 "2330"
            date: 查詢月份 YYYYMMDD（日期隨意，例如 "20250101" 查 2025 年 1 月）

        Returns:
            該月份的每日收盤均價資料
        """
        resp = _client.fetch_json(
            STOCK_DAY_AVG_URL,
            params={"response": "json", "stockNo": stock_no, "date": date},
        )

        if not resp or resp.get("stat") != "OK":
            return f"查無 {stock_no} 在 {date} 的月均價資料，請確認該日期為交易日（非假日或週末）"

        data = resp.get("data", [])
        if not data:
            return f"查無 {stock_no} 在 {date[:6]} 的月均價資料"

        title = resp.get("title", f"{stock_no} 月均價")
        lines = [f"【{title}】\n"]

        for row in data:
            # row: [日期, 收盤均價]
            # Last row may be a summary (e.g. "月平均收盤價") — not a date
            if "/" not in row[0]:
                lines.append(f"{row[0]}: {row[1] if len(row) > 1 else 'N/A'}")
                continue
            ad_date = roc_to_ad(row[0])
            avg_price = row[1] if len(row) > 1 else "N/A"
            lines.append(f"日期: {ad_date} | 收盤均價: {avg_price}")

        return "\n".join(lines)
