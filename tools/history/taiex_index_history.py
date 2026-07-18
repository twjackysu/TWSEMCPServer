"""TWSE 發行量加權股價指數 (TAIEX) daily OHLC history (whole month per call)."""

from typing import Optional
from fastmcp import FastMCP
from utils import TWSEAPIClient, handle_api_errors

MI_5MINS_HIST_URL = "https://www.twse.com.tw/rwd/zh/TAIEX/MI_5MINS_HIST"


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    """Register TAIEX daily OHLC history tools."""
    _client = client or TWSEAPIClient.get_instance()

    @mcp.tool
    @handle_api_errors()
    def get_taiex_index_history(date: str) -> str:
        """查詢發行量加權股價指數（大盤）每日開高低收歷史資料。
        與個股的 get_stock_history 對應，但查的是大盤指數本身，適合大盤走勢/K線分析。
        與 get_market_historical_index（openapi 版）不同：openapi 版只回傳最近約 12 個交易日的
        滾動視窗，無法指定過去月份；此工具可查任意過去月份。

        Args:
            date: 欲查詢的月份，格式 YYYYMMDD（日期隨意，例如 "20260601" 查 2026 年 6 月整月）

        Returns:
            該月份每個交易日的加權指數開盤、最高、最低、收盤指數
        """
        resp = _client.fetch_json(
            MI_5MINS_HIST_URL,
            params={"response": "json", "date": date},
        )

        if not resp or resp.get("stat") != "OK":
            return f"查無 {date[:6]} 的加權指數歷史資料，請確認日期是否有效"

        data = resp.get("data", [])
        if not data:
            return f"查無 {date[:6]} 的加權指數歷史資料"

        title = resp.get("title", f"{date[:6]} 發行量加權股價指數歷史資料")
        lines = [f"【{title}】\n"]
        for row in data:
            # row: 日期,開盤指數,最高指數,最低指數,收盤指數
            d, o, h, l, c = row
            lines.append(f"{d} | 開:{o} 高:{h} 低:{l} 收:{c}")

        return "\n".join(lines)
