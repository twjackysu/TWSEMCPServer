"""TWSE market-level 三大法人 (institutional investor) buy/sell amounts: one day, a week or a month.

Source: www.twse.com.tw/rwd/zh/fund/BFI82U (三大法人買賣金額統計表), amounts in 元.
- ``type=day``: ``dayDate`` optional, latest trading day without it.
- ``type=week``: ``weekDate`` must be the week's first trading day — the Monday, or the Tuesday
  when Monday is a holiday (2026-04-06 → no data, 2026-04-07 → that week). No date → no data.
- ``type=month``: ``monthDate`` any day of the month (the current month runs to date). No date
  → an HTML page, so a date is always sent.
Read through the BFI82U gateway (``sources.twse.bfi82u``).
"""

from datetime import datetime, timedelta
from typing import Optional

from fastmcp import FastMCP
from sources.twse.bfi82u import institutional_amounts
from utils import TWSEAPIClient, printed
from toolkit import TradingDate, handle_api_errors
from utils.institutional import PERIODS, Period, week_start, yi


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    """Register TWSE market-level institutional amount tools."""
    _client = client or TWSEAPIClient.get_instance()

    @mcp.tool
    @handle_api_errors()
    def get_market_institutional_amounts_history(date: TradingDate = "", period: Period = "day") -> str:
        """查詢上市市場「整體」三大法人（外資及陸資、投信、自營商）的買賣金額：買進、賣出與買賣超金額（市場層級總額，
        不是個股）：預設最新交易日，可查任意過去交易日，也可查整週或整月的累計金額。
        適合回答「外資今天／上週／這個月在上市市場總共買超或賣超多少錢」。
        個股的法人買賣超排行請用 get_twse_institutional_investors_summary；單一個股明細請用
        get_twse_institutional_investors_by_stock；上櫃市場請用 get_otc_institutional_summary。

        回傳：自營商（自行買賣／避險）、投信、外資及陸資（不含外資自營商）、外資自營商與三大法人合計的
        買進、賣出、買賣差額（億元；買賣差額另附原始元）

        Args:
            date: 日期 西元 YYYYMMDD（選填，留空＝最新交易日）。period 為 week／month 時指該日所在的週或月
            period: day（單日，預設）、week（該週合計）、month（該月合計，當月為月初至今）
        """
        date = date.strip()
        anchor = datetime.strptime(date, "%Y%m%d") if date else None

        if period == "day":
            report = institutional_amounts(_client, "day", date)
        else:
            if anchor is None:
                latest = institutional_amounts(_client, "day")
                if latest is None:
                    return "查無最新交易日的三大法人買賣金額統計"
                anchor = datetime.strptime(latest.date, "%Y%m%d")
            if period == "month":
                report = institutional_amounts(_client, "month", f"{anchor:%Y%m%d}")
            else:
                report = None
                # 週資料要用該週第一個交易日查詢：週一休市時改用週二，以此類推
                for offset in range(5):
                    report = institutional_amounts(_client, "week", f"{week_start(anchor) + timedelta(days=offset):%Y%m%d}")
                    if report is not None:
                        break

        if report is None:
            label = date or "最新交易日"
            return f"查無 {label} 的三大法人買賣金額統計（{PERIODS[period]}），請確認該日期為交易日（非假日或週末）"

        lines = [f"【{report.title or '三大法人買賣金額統計表'}】（單位：億元）\n"]
        for a in report.amounts:
            lines.append(f"{a.name}：買進 {yi(a.buy)} | 賣出 {yi(a.sell)} | 買賣差額 {yi(a.net)}（{printed(a.net)} 元）")
        return "\n".join(lines)
