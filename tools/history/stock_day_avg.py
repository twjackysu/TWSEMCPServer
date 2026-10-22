"""Per-stock daily closes and monthly average close (日收盤價及月平均收盤價), any month.

Replaces the OpenAPI /exchangeReport/STOCK_DAY_AVG_ALL tool: per stock it only gave the
latest close and this month's average, which on 2026-09-29 equalled this endpoint's
月平均收盤價 row; this endpoint also lists every day's close and accepts past months.
Read through the STOCK_DAY_AVG gateway (``sources.twse.stock_day_avg``).
"""

from typing import Optional
from fastmcp import FastMCP
from sources.twse.stock_day_avg import AVERAGE_LABEL, monthly_closes
from utils import TWSEAPIClient, plain, printed
from toolkit import TradingDate, handle_api_errors


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    """Register stock monthly average tools."""
    _client = client or TWSEAPIClient.get_instance()

    @mcp.tool
    @handle_api_errors()
    def get_stock_monthly_average(stock_no: str, date: TradingDate = "") -> str:
        """查詢上市個股當月每日收盤價及月平均收盤價：預設本月，也可查任意過去月份，適合評估月線趨勢。

        回傳：該月份每個交易日的收盤價，以及月平均收盤價

        Args:
            stock_no: 股票代號，例如 "2330"
            date: 查詢月份 西元 YYYYMMDD（日期隨意，例如 "20250101" 查 2025 年 1 月；留空＝本月）
        """
        month = monthly_closes(_client, stock_no, date)
        date = date or (month.date if month else "") or "本月"

        if month is None:
            return f"查無 {stock_no} 在 {date} 的月均價資料，請確認該日期為交易日（非假日或週末）"
        if not month.closes and month.average is None:
            return f"查無 {stock_no} 在 {date[:6]} 的月均價資料"

        lines = [f"【{month.title or f'{stock_no} 月均價'}】\n"]
        lines += [f"日期: {c.day:%Y-%m-%d} | 收盤價: {printed(c.close)}" for c in month.closes]
        if month.average is not None:
            lines.append(f"{AVERAGE_LABEL}: {plain(month.average)}")  # TWSE prints it without thousands separators
        return "\n".join(lines)
