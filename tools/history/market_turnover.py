"""TWSE daily market turnover history (whole month per call), through the FMTQIK gateway (``sources.twse.fmtqik``)."""

from typing import Optional
from fastmcp import FastMCP
from sources.twse.fmtqik import market_turnover
from utils import TWSEAPIClient, printed
from utils.date_helper import roc_day
from toolkit import TradingDate, handle_api_errors


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    """Register TWSE market turnover history tools."""
    _client = client or TWSEAPIClient.get_instance()

    @mcp.tool
    @handle_api_errors()
    def get_market_turnover_history(date: TradingDate = "") -> str:
        """查詢台灣上市市場每日成交量值（成交量、成交值，觀察量能）與發行量加權股價指數。
        回傳指定月份每一個交易日的市場成交股數、成交金額、成交筆數、加權指數收盤與漲跌點數。
        與 get_daily_market_trading_info（openapi 版）不同：openapi 版只回傳最近約 12 個交易日的
        滾動視窗，無法指定過去月份；此工具可查任意過去月份。

        回傳：該月份每個交易日的成交股數、成交金額、成交筆數、加權指數、漲跌點數

        Args:
            date: 欲查詢的月份，格式 西元 YYYYMMDD（日期隨意，例如 "20260601" 查 2026 年 6 月整月；留空＝本月）
        """
        month = market_turnover(_client, date)
        date = date or (month.date if month else "") or "本月"

        if month is None:
            return f"查無 {date[:6]} 的市場成交資訊，請確認日期是否有效"
        if not month.days:
            return f"查無 {date[:6]} 的市場成交資訊"

        lines = [f"【{month.title or f'{date[:6]} 市場成交資訊'}】\n"]
        for d in month.days:
            lines.append(
                f"{roc_day(d.day)} | 加權指數:{printed(d.index)}（{printed(d.change)}）| 成交量:{printed(d.volume)} | "
                f"成交金額:{printed(d.value)} | 筆數:{printed(d.transactions)}"
            )

        return "\n".join(lines)
