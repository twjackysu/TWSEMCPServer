"""TWSE market-level 三大法人 (institutional investor) buy/sell amount statistics."""

from typing import Optional
from fastmcp import FastMCP
from utils import TWSEAPIClient, handle_api_errors

BFI82U_URL = "https://www.twse.com.tw/rwd/zh/fund/BFI82U"


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    """Register TWSE market-level institutional amount tools."""
    _client = client or TWSEAPIClient.get_instance()

    @mcp.tool
    @handle_api_errors()
    def get_market_institutional_amounts_history(date: str, period: str = "day") -> str:
        """查詢台灣上市市場三大法人（自營商、投信、外資及陸資）買賣金額統計表。
        與 get_twse_institutional_investors_summary（個股買賣超股數）不同，此工具回傳的是
        「市場層級」的買賣「金額」總計，適合快速回答「外資今天整體買超/賣超多少」。

        Args:
            date: 查詢日期，格式 YYYYMMDD，例如 "20260610"（需為交易日）
            period: 統計區間，"day"（日）、"week"（週）或 "month"（月），預設 "day"

        Returns:
            自營商（自行買賣/避險）、投信、外資及陸資（含外資自營商）的買進/賣出/買賣差額金額（元），及三大法人合計
        """
        resp = _client.fetch_json(
            BFI82U_URL,
            params={"response": "json", "dayDate": date, "type": period},
        )

        if not resp or resp.get("stat") != "OK":
            return f"查無 {date} 的三大法人買賣金額統計，請確認該日期為交易日（非假日或週末）"

        data = resp.get("data", [])
        if not data:
            return f"查無 {date} 的三大法人買賣金額統計"

        title = resp.get("title", f"{date} 三大法人買賣金額統計表")
        lines = [f"【{title}】\n"]
        for row in data:
            name, buy, sell, net = row[0], row[1], row[2], row[3]
            lines.append(f"{name}：買進 {buy} 元 | 賣出 {sell} 元 | 買賣差額 {net} 元")

        return "\n".join(lines)
