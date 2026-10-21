"""Historical daily OHLCV data for individual stocks."""

from datetime import datetime
from typing import Optional
from fastmcp import FastMCP
from utils import TWSEAPIClient
from toolkit import RequiredTradingDate, handle_api_errors
from sources.twse.stock_day import stock_day_month


def _text(value) -> str:
    """A number as TWSE prints it without thousands separators; "--" where it has none."""
    return "--" if value is None else str(value)


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    """Register historical stock day tools."""
    _client = client or TWSEAPIClient.get_instance()

    @mcp.tool
    @handle_api_errors()
    def get_stock_history(stock_no: str, date: RequiredTradingDate) -> str:
        """查詢台灣上市股票歷史日K資料。
        一次回傳指定月份的每日 OHLCV 資料，從 2010 年至今皆可查。

        回傳：該月份每日交易資料，含日期(西元)、開盤價、最高價、最低價、收盤價、成交量、成交金額

        Args:
            stock_no: 股票代號，例如 "2330"（台積電）、"0050"（元大台灣50）
            date: 欲查詢的月份，格式 西元 YYYYMMDD（日期隨意，例如 "20250101" 查 2025 年 1 月整月）
        """
        day = datetime.strptime(date, "%Y%m%d")

        month = stock_day_month(_client, stock_no.strip(), day.year, day.month)
        if month is None:
            return f"查無 {stock_no} 在 {date} 的交易資料，請確認該日期為交易日（非假日或週末）"

        lines = [f"【{month.title or f'{stock_no} 歷史日K'}】\n"]
        for row in month.rows:
            lines.append(
                f"日期: {row.day.isoformat()} | 開: {_text(row.open)} | 高: {_text(row.high)} | "
                f"低: {_text(row.low)} | 收: {_text(row.close)} | 漲跌: {row.change} | "
                f"成交量: {_text(row.volume)} | 成交金額: {_text(row.value)} | 筆數: {_text(row.transactions)}"
            )

        return "\n".join(lines)
