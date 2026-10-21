"""OTC market-level 三大法人 buy/sell amounts (三大法人買賣金額彙總表): a day, a week or a month.

Source: www.tpex.org.tw/www/zh-tw/insti/summary (``type`` Daily / Weekly / Monthly, ``date``
YYYY/MM/DD — any day of that week or month — ``prod`` 1 上櫃股票 / 0 上櫃有價證券), amounts in 元.
It replaces the openapi tpex_3insti_summary source: on 2026-10-19 all 8 rows (外資及陸資合計
and its two parts, 投信, 自營商合計 and its two parts, 三大法人合計) matched prod=1 Daily
exactly; the website endpoint adds past dates, weekly / monthly totals and prod=0.
"""

from typing import Literal, Optional

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from utils import TWSEAPIClient
from toolkit import handle_api_errors
from utils.institutional import PERIODS, Period, yi
from .history import TPEX_WWW, date_params, first_table, resp_date

INSTI_SUMMARY_URL = f"{TPEX_WWW}/insti/summary"
TPEX_PERIODS = {"day": "Daily", "week": "Weekly", "month": "Monthly"}
SCOPES = {"stocks": ("1", "上櫃股票"), "all": ("0", "上櫃有價證券（含 ETF 等）")}
Scope = Literal["stocks", "all"]  # SCOPES


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    """Register OTC institutional summary tools."""
    _client = client or TWSEAPIClient.get_instance()

    @mcp.tool
    @handle_api_errors()
    def get_otc_institutional_summary(date: str = "", period: Period = "day", scope: Scope = "stocks") -> str:
        """查詢上櫃市場「整體」三大法人（外資及陸資、投信、自營商）的買進、賣出與買賣超金額（市場層級總額，
        不是個股）：預設最新交易日，可查任意過去交易日，也可查整週或整月的累計金額。
        上櫃個股的法人買賣超請用 get_otc_institutional；上市市場請用 get_market_institutional_amounts_history。

        回傳：外資及陸資合計（及其中不含自營商、外資自營商兩項）、投信、自營商合計（及其中自行買賣、避險兩項）、
        三大法人合計的買進、賣出、買賣超金額（億元；買賣超另附原始元）

        Args:
            date: 日期 YYYYMMDD（選填，留空＝最新交易日）。period 為 week／month 時指該日所在的週或月
            period: day（單日，預設）、week（該週合計）、month（該月合計，當月為月初至今）
            scope: stocks（上櫃股票，預設）或 all（上櫃全部有價證券，含 ETF 等）
        """
        params = date_params(date)
        if params is None:
            raise ToolError("日期格式錯誤，請使用 YYYYMMDD，例如 \"20261016\"")
        prod, scope_label = SCOPES[scope]
        resp = _client.fetch_json(
            INSTI_SUMMARY_URL,
            params={"type": TPEX_PERIODS[period], "prod": prod, **params, "response": "json"},
        )
        table = first_table(resp)
        rows = table.get("data") or []
        if not rows:
            return (f"查無 {date or '最新交易日'} 的上櫃三大法人買賣金額（{PERIODS[period]}），"
                    "請確認該日期為交易日（非假日或週末）")

        heading = table.get("subtitle") or f"{resp_date(resp, date)} {scope_label}三大法人買賣金額"
        lines = [f"【{heading}】（單位：億元）\n"]
        for name, buy, sell, net in (row[:4] for row in rows):
            lines.append(f"{name.strip()}：買進 {yi(buy)} | 賣出 {yi(sell)} | 買賣超 {yi(net)}（{net} 元）")
        return "\n".join(lines)
