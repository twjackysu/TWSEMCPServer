"""Historical daily OHLCV data for individual stocks."""

from typing import Optional
from fastmcp import FastMCP
from utils import TWSEAPIClient, handle_api_errors, roc_to_ad

STOCK_DAY_URL = "https://www.twse.com.tw/exchangeReport/STOCK_DAY"


def _parse_number(value: str) -> str:
    """Remove commas from number strings, return as-is if not parseable."""
    return value.replace(",", "")


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    """Register historical stock day tools."""
    _client = client or TWSEAPIClient.get_instance()

    @mcp.tool
    @handle_api_errors()
    def get_stock_history(stock_no: str, date: str) -> str:
        """查詢台灣上市股票歷史日K資料。
        一次回傳指定月份的每日 OHLCV 資料，從 2010 年至今皆可查。

        Args:
            stock_no: 股票代號，例如 "2330"（台積電）、"0050"（元大台灣50）
            date: 欲查詢的月份，格式 YYYYMMDD（日期隨意，例如 "20250101" 查 2025 年 1 月整月）

        Returns:
            該月份每日交易資料，含日期(西元)、開盤價、最高價、最低價、收盤價、成交量、成交金額
        """
        resp = _client.fetch_json(
            STOCK_DAY_URL,
            params={"response": "json", "stockNo": stock_no, "date": date},
        )

        if not resp or resp.get("stat") != "OK":
            return f"查無 {stock_no} 在 {date} 的交易資料，請確認該日期為交易日（非假日或週末）"

        data = resp.get("data", [])
        if not data:
            return f"查無 {stock_no} 在 {date[:6]} 的交易資料"

        title = resp.get("title", f"{stock_no} 歷史日K")
        lines = [f"【{title}】\n"]

        for row in data:
            # row: [日期, 成交股數, 成交金額, 開盤價, 最高價, 最低價, 收盤價, 漲跌價差, 成交筆數]
            ad_date = roc_to_ad(row[0])
            volume = _parse_number(row[1])
            trade_value = _parse_number(row[2])
            open_price = _parse_number(row[3])
            high = _parse_number(row[4])
            low = _parse_number(row[5])
            close = _parse_number(row[6])
            change = row[7]
            transactions = _parse_number(row[8])

            lines.append(
                f"日期: {ad_date} | 開: {open_price} | 高: {high} | "
                f"低: {low} | 收: {close} | 漲跌: {change} | "
                f"成交量: {volume} | 成交金額: {trade_value} | 筆數: {transactions}"
            )

        return "\n".join(lines)
