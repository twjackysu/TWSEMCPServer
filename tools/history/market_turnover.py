"""TWSE daily market turnover history (whole month per call)."""

from typing import Optional
from fastmcp import FastMCP
from utils import TWSEAPIClient, handle_api_errors

FMTQIK_URL = "https://www.twse.com.tw/rwd/zh/afterTrading/FMTQIK"


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    """Register TWSE market turnover history tools."""
    _client = client or TWSEAPIClient.get_instance()

    @mcp.tool
    @handle_api_errors()
    def get_market_turnover_history(date: str) -> str:
        """查詢台灣上市市場每日成交量值與發行量加權股價指數。
        回傳指定月份每一個交易日的市場成交股數、成交金額、成交筆數、加權指數收盤與漲跌點數。
        與 get_daily_market_trading_info（openapi 版）不同：openapi 版只回傳最近約 12 個交易日的
        滾動視窗，無法指定過去月份；此工具可查任意過去月份。

        Args:
            date: 欲查詢的月份，格式 YYYYMMDD（日期隨意，例如 "20260601" 查 2026 年 6 月整月）

        Returns:
            該月份每個交易日的成交股數、成交金額、成交筆數、加權指數、漲跌點數
        """
        resp = _client.fetch_json(
            FMTQIK_URL,
            params={"response": "json", "date": date},
        )

        if not resp or resp.get("stat") != "OK":
            return f"查無 {date[:6]} 的市場成交資訊，請確認日期是否有效"

        data = resp.get("data", [])
        if not data:
            return f"查無 {date[:6]} 的市場成交資訊"

        title = resp.get("title", f"{date[:6]} 市場成交資訊")
        lines = [f"【{title}】\n"]
        for row in data:
            # row: 日期,成交股數,成交金額,成交筆數,發行量加權股價指數,漲跌點數
            d, volume, value, tx, index, change = row
            lines.append(
                f"{d} | 加權指數:{index}（{change}）| 成交量:{volume} | 成交金額:{value} | 筆數:{tx}"
            )

        return "\n".join(lines)
