"""TAIFEX 三大法人期貨／選擇權分計 (futures and options side by side), latest day or any period.

Source: www.taifex.com.tw download page futAndOptDateDown (``sources.taifex.institutional``). Replaces the
openapi MarketDataOfMajorInstitutionalTradersDividedByFuturesAndOptionsBytheDate tool and the former
get_institutional_fut_opt_split_history; on 2026-09-29 all three identity rows matched the
openapi endpoint value for value.
"""

from typing import Optional
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from sources.taifex.institutional import Positions, institutional_split
from utils import TWSEAPIClient, cap_rows, plain
from toolkit import TradingDate, handle_api_errors
from utils.taifex import fetch_period

# No server-enforced span cap observed (a 3-month pull works); retention runs out ~3 years back.
MAX_SPAN_DAYS = 92
MAX_OUTPUT_ROWS = 300


def _summary(p: Positions) -> str:
    return (f"交易 多{plain(p.long_volume)}/空{plain(p.short_volume)}/淨{plain(p.net_volume)}"
            f"（淨額 {plain(p.net_value)} 千元）| "
            f"未平倉 多{plain(p.long_oi)}/空{plain(p.short_oi)}/淨{plain(p.net_oi)}"
            f"（淨額 {plain(p.net_oi_value)} 千元）")


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    """Register TAIFEX institutional futures/options split tools."""
    _client = client or TWSEAPIClient.get_instance()

    @mcp.tool
    @handle_api_errors()
    def get_futures_institutional(start_date: TradingDate = "", end_date: TradingDate = "") -> str:
        """查詢三大法人（自營商、投信、外資及陸資）期貨與選擇權分計交易：預設最新交易日，
        也可回溯任意區間（最長 92 天，約近 3 年內）。外資期貨淨未平倉是台股最常引用的籌碼指標之一；
        期貨與選擇權並列，方便比較兩者布局是否一致。期貨+選擇權合計請用 get_institutional_general。

        回傳：每個交易日、每個身份別的期貨與選擇權各自多空交易口數、契約金額（千元）、未平倉口數與契約金額

        Args:
            start_date: 起始日期 西元 YYYYMMDD（選填，留空＝最新交易日）
            end_date: 結束日期 西元 YYYYMMDD（選填，預設同 start_date）。區間不可超過 92 天
        """
        rows, label, error = fetch_period(lambda s, e: institutional_split(_client, s, e),
                                          start_date, end_date, MAX_SPAN_DAYS)
        if error:
            raise ToolError(error)
        if rows is None:
            return f"查無 {label} 的三大法人期貨/選擇權分計資料，日期區間可能超出資料保存範圍（約近 3 年內）"

        total = len(rows)
        shown, cap_note = cap_rows(rows, MAX_OUTPUT_ROWS, "請縮小 start_date～end_date")
        lines = [f"【三大法人期貨/選擇權分計】{label}（共 {total} 筆{cap_note}）\n"]
        for r in shown:
            lines.append(
                f"{r.day:%Y/%m/%d} | {r.identity}\n"
                f"  期貨: {_summary(r.futures)}\n"
                f"  選擇權: {_summary(r.options)}"
            )
        return "\n".join(lines)
