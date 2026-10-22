"""TAIFEX 三大法人 futures + options combined totals (總表), latest day or any period.

Source: www.taifex.com.tw download page totalTableDateDown (``sources.taifex.institutional``). Replaces the
openapi MarketDataOfMajorInstitutionalTradersGeneralBytheDate tool and the former
get_institutional_total_history; on 2026-09-29 the three identity rows matched the openapi
endpoint (served as CSV that day) value for value.
"""

from typing import Optional
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from sources.taifex.institutional import institutional_totals
from utils import TWSEAPIClient, cap_rows, plain
from toolkit import TradingDate, handle_api_errors
from utils.taifex import fetch_period

# No server-enforced span cap observed (3-month pulls work); retention runs out ~3 years back.
MAX_SPAN_DAYS = 92
MAX_OUTPUT_ROWS = 300


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    _client = client or TWSEAPIClient.get_instance()

    @mcp.tool
    @handle_api_errors()
    def get_institutional_general(start_date: TradingDate = "", end_date: TradingDate = "") -> str:
        """查詢三大法人（自營商、投信、外資及陸資）期貨與選擇權「合計」的整體交易總表：
        預設最新交易日，也可回溯任意區間（最長 92 天，約近 3 年內）。
        期貨、選擇權分開並列請用 get_futures_institutional。

        回傳：每個交易日、每個身份別的交易口數與金額（多/空/淨）、未平倉口數及契約價值（百萬元）

        Args:
            start_date: 起始日期 西元 YYYYMMDD（選填，留空＝最新交易日）
            end_date: 結束日期 西元 YYYYMMDD（選填，預設同 start_date）。區間不可超過 92 天
        """
        rows, label, error = fetch_period(lambda s, e: institutional_totals(_client, s, e),
                                          start_date, end_date, MAX_SPAN_DAYS)
        if error:
            raise ToolError(error)
        if rows is None:
            return f"查無 {label} 的三大法人期貨+選擇權總表資料，日期區間可能超出資料保存範圍（約近 3 年內）"

        total = len(rows)
        shown, cap_note = cap_rows(rows, MAX_OUTPUT_ROWS, "請縮小 start_date～end_date")
        lines = [f"【三大法人整體交易總表（期貨+選擇權）】{label}（共 {total} 筆{cap_note}）\n"]
        for r in shown:
            p = r.positions
            lines.append(
                f"{r.day:%Y/%m/%d} | {r.identity}\n"
                f"  交易量: 多 {plain(p.long_volume)} / 空 {plain(p.short_volume)} / 淨 {plain(p.net_volume)}\n"
                f"  交易金額(百萬): 多 {plain(p.long_value)} / 空 {plain(p.short_value)} / 淨 {plain(p.net_value)}\n"
                f"  未平倉口數: 多 {plain(p.long_oi)} / 空 {plain(p.short_oi)} / 淨 {plain(p.net_oi)}\n"
                f"  未平倉契約價值(百萬): 多 {plain(p.long_oi_value)} / 空 {plain(p.short_oi_value)} / "
                f"淨 {plain(p.net_oi_value)}"
            )
        return "\n".join(lines)
