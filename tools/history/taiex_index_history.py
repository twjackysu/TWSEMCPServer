"""TWSE 發行量加權股價指數 (TAIEX) daily OHLC history (whole month per call).

Replaces the OpenAPI /indicesReport/MI_5MINS_HIST tool (get_market_historical_index): it only
served the current month, whose rows on 2026-09-29 were identical to this endpoint's.
Read through the MI_5MINS_HIST gateway (``sources.twse.mi_5mins_hist``).
"""

from typing import Optional
from fastmcp import FastMCP
from sources.twse.mi_5mins_hist import taiex_history
from utils import TWSEAPIClient, printed
from utils.date_helper import roc_day
from toolkit import TradingDate, handle_api_errors


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    """Register TAIEX daily OHLC history tools."""
    _client = client or TWSEAPIClient.get_instance()

    @mcp.tool
    @handle_api_errors()
    def get_taiex_index_history(date: TradingDate = "") -> str:
        """查詢發行量加權股價指數（大盤）每日開高低收：預設本月，也可查任意過去月份。
        與個股的 get_stock_history 對應，但查的是大盤指數本身，適合大盤走勢/K線分析。

        回傳：該月份每個交易日的加權指數開盤、最高、最低、收盤指數

        Args:
            date: 欲查詢的月份，格式 西元 YYYYMMDD（日期隨意，例如 "20260601" 查 2026 年 6 月整月；留空＝本月）
        """
        month = taiex_history(_client, date)
        date = date or (month.date if month else "") or "本月"

        if month is None:
            return f"查無 {date[:6]} 的加權指數歷史資料，請確認日期是否有效"
        if not month.days:
            return f"查無 {date[:6]} 的加權指數歷史資料"

        lines = [f"【{month.title or f'{date[:6]} 發行量加權股價指數歷史資料'}】\n"]
        for d in month.days:
            lines.append(f"{roc_day(d.day)} | 開:{printed(d.open)} 高:{printed(d.high)} 低:{printed(d.low)} "
                         f"收:{printed(d.close)}")

        return "\n".join(lines)
