"""TAIFEX 三大法人 futures + options combined totals (總表), latest day or any period.

Source: www.taifex.com.tw download page totalTableDateDown. Replaces the openapi
MarketDataOfMajorInstitutionalTradersGeneralBytheDate tool and the former
get_institutional_total_history; on 2026-09-29 the three identity rows matched the openapi
endpoint (served as CSV that day) value for value.
"""

from typing import Optional
from fastmcp import FastMCP
from utils import TWSEAPIClient, handle_api_errors, cap_rows
from utils.taifex import (
    TAIFEX_DOWNLOAD_BASE,
    TAIFEX_HEADERS,
    decode_and_parse_csv,
    download_form,
    fetch_period,
)

TOTAL_TABLE_DATE_DOWN_URL = f"{TAIFEX_DOWNLOAD_BASE}/totalTableDateDown"
# No server-enforced span cap observed (3-month pulls work); retention runs out ~3 years back.
MAX_SPAN_DAYS = 92
MAX_OUTPUT_ROWS = 300


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    _client = client or TWSEAPIClient.get_instance()

    def fetch(start_dt, end_dt):
        body = _client.fetch_bytes(
            TOTAL_TABLE_DATE_DOWN_URL,
            method="POST",
            headers=TAIFEX_HEADERS,
            data=download_form(start_dt, end_dt),
        )
        return decode_and_parse_csv(body)

    @mcp.tool
    @handle_api_errors()
    def get_institutional_general(start_date: str = "", end_date: str = "") -> str:
        """查詢三大法人（自營商、投信、外資及陸資）期貨與選擇權「合計」的整體交易總表：
        預設最新交易日，也可回溯任意區間（最長 92 天，約近 3 年內）。
        期貨、選擇權分開並列請用 get_futures_institutional。

        Args:
            start_date: 起始日期 YYYYMMDD（選填，留空＝最新交易日）
            end_date: 結束日期 YYYYMMDD（選填，預設同 start_date）。區間不可超過 92 天

        Returns:
            每個交易日、每個身份別的交易口數與金額（多/空/淨）、未平倉口數及契約價值（百萬元）
        """
        parsed, label, error = fetch_period(fetch, start_date, end_date, MAX_SPAN_DAYS, "20260401")
        if error:
            return error
        if parsed is None:
            return f"查無 {label} 的三大法人期貨+選擇權總表資料，日期區間可能超出資料保存範圍（約近 3 年內）"

        rows = parsed[1]
        total = len(rows)
        shown, cap_note = cap_rows(rows, MAX_OUTPUT_ROWS, "請縮小 start_date～end_date")
        lines = [f"【三大法人整體交易總表（期貨+選擇權）】{label}（共 {total} 筆{cap_note}）\n"]
        for r in shown:
            # r: 日期,身份別,多方交易口數,多方交易契約金額,空方交易口數,空方交易契約金額,淨口數,淨金額,
            #    多方未平倉口數,多方未平倉契約金額,空方未平倉口數,空方未平倉契約金額,淨未平倉口數,淨未平倉契約金額
            lines.append(
                f"{r[0]} | {r[1]}\n"
                f"  交易量: 多 {r[2]} / 空 {r[4]} / 淨 {r[6]}\n"
                f"  交易金額(百萬): 多 {r[3]} / 空 {r[5]} / 淨 {r[7]}\n"
                f"  未平倉口數: 多 {r[8]} / 空 {r[10]} / 淨 {r[12]}\n"
                f"  未平倉契約價值(百萬): 多 {r[9]} / 空 {r[11]} / 淨 {r[13]}"
            )
        return "\n".join(lines)
