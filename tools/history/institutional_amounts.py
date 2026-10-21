"""TWSE market-level 三大法人 (institutional investor) buy/sell amounts: one day, a week or a month.

Source: www.twse.com.tw/rwd/zh/fund/BFI82U (三大法人買賣金額統計表), amounts in 元.
- ``type=day``: ``dayDate`` optional, latest trading day without it.
- ``type=week``: ``weekDate`` must be the week's first trading day — the Monday, or the Tuesday
  when Monday is a holiday (2026-04-06 → no data, 2026-04-07 → that week). No date → no data.
- ``type=month``: ``monthDate`` any day of the month (the current month runs to date). No date
  → an HTML page, so a date is always sent.
"""

from datetime import datetime, timedelta
from typing import Optional

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from utils import TWSEAPIClient
from toolkit import handle_api_errors
from utils.institutional import PERIODS, check_choice, week_start, yi

BFI82U_URL = "https://www.twse.com.tw/rwd/zh/fund/BFI82U"


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    """Register TWSE market-level institutional amount tools."""
    _client = client or TWSEAPIClient.get_instance()

    def _fetch(**params) -> dict:
        resp = _client.fetch_json(BFI82U_URL, params={"response": "json", **params})
        return resp if isinstance(resp, dict) and resp.get("stat") == "OK" and resp.get("data") else {}

    @mcp.tool
    @handle_api_errors()
    def get_market_institutional_amounts_history(date: str = "", period: str = "day") -> str:
        """查詢上市市場「整體」三大法人（外資及陸資、投信、自營商）的買進、賣出與買賣超金額（市場層級總額，
        不是個股）：預設最新交易日，可查任意過去交易日，也可查整週或整月的累計金額。
        適合回答「外資今天／上週／這個月在上市市場總共買超或賣超多少錢」。
        個股的法人買賣超排行請用 get_twse_institutional_investors_summary；單一個股明細請用
        get_twse_institutional_investors_by_stock；上櫃市場請用 get_otc_institutional_summary。

        回傳：自營商（自行買賣／避險）、投信、外資及陸資（不含外資自營商）、外資自營商與三大法人合計的
        買進、賣出、買賣差額（億元；買賣差額另附原始元）

        Args:
            date: 日期 YYYYMMDD（選填，留空＝最新交易日）。period 為 week／month 時指該日所在的週或月
            period: day（單日，預設）、week（該週合計）、month（該月合計，當月為月初至今）
        """
        error = check_choice("period", period, PERIODS)
        if error:
            raise ToolError(error)
        date = date.strip()
        try:
            anchor = datetime.strptime(date, "%Y%m%d") if date else None
        except ValueError:
            raise ToolError("日期格式錯誤，請使用 YYYYMMDD，例如 \"20261016\"") from None

        if period == "day":
            resp = _fetch(type="day", dayDate=date) if date else _fetch(type="day")
        else:
            if anchor is None:
                latest = _fetch(type="day")
                if not latest:
                    return "查無最新交易日的三大法人買賣金額統計"
                anchor = datetime.strptime(str(latest["date"]), "%Y%m%d")
            if period == "month":
                resp = _fetch(type="month", monthDate=f"{anchor:%Y%m%d}")
            else:
                resp = {}
                # 週資料要用該週第一個交易日查詢：週一休市時改用週二，以此類推
                for offset in range(5):
                    resp = _fetch(type="week", weekDate=f"{week_start(anchor) + timedelta(days=offset):%Y%m%d}")
                    if resp:
                        break

        if not resp:
            label = date or "最新交易日"
            return f"查無 {label} 的三大法人買賣金額統計（{PERIODS[period]}），請確認該日期為交易日（非假日或週末）"

        lines = [f"【{resp.get('title', '三大法人買賣金額統計表')}】（單位：億元）\n"]
        for name, buy, sell, net in (row[:4] for row in resp["data"]):
            lines.append(f"{name}：買進 {yi(buy)} | 賣出 {yi(sell)} | 買賣差額 {yi(net)}（{net} 元）")
        return "\n".join(lines)
