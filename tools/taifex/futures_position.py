"""TAIFEX 三大法人期貨／選擇權分計 (futures and options side by side), latest day or any period.

Source: www.taifex.com.tw download page futAndOptDateDown. Replaces the openapi
MarketDataOfMajorInstitutionalTradersDividedByFuturesAndOptionsBytheDate tool and the former
get_institutional_fut_opt_split_history; on 2026-09-29 all three identity rows matched the
openapi endpoint value for value.
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

FUT_AND_OPT_DATE_DOWN_URL = f"{TAIFEX_DOWNLOAD_BASE}/futAndOptDateDown"
# No server-enforced span cap observed (a 3-month pull works); retention runs out ~3 years back.
MAX_SPAN_DAYS = 92
MAX_OUTPUT_ROWS = 300


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    """Register TAIFEX institutional futures/options split tools."""
    _client = client or TWSEAPIClient.get_instance()

    def fetch(start_dt, end_dt):
        body = _client.fetch_bytes(
            FUT_AND_OPT_DATE_DOWN_URL,
            method="POST",
            headers=TAIFEX_HEADERS,
            data=download_form(start_dt, end_dt),
        )
        return decode_and_parse_csv(body)

    @mcp.tool
    @handle_api_errors()
    def get_futures_institutional(start_date: str = "", end_date: str = "") -> str:
        """查詢三大法人（自營商、投信、外資及陸資）期貨與選擇權分計交易：預設最新交易日，
        也可回溯任意區間（最長 92 天，約近 3 年內）。外資期貨淨未平倉是台股最常引用的籌碼指標之一；
        期貨與選擇權並列，方便比較兩者布局是否一致。期貨+選擇權合計請用 get_institutional_general。

        Args:
            start_date: 起始日期 YYYYMMDD（選填，留空＝最新交易日）
            end_date: 結束日期 YYYYMMDD（選填，預設同 start_date）。區間不可超過 92 天

        Returns:
            每個交易日、每個身份別的期貨與選擇權各自多空交易口數、契約金額（千元）、未平倉口數與契約金額
        """
        parsed, label, error = fetch_period(fetch, start_date, end_date, MAX_SPAN_DAYS, "20260401")
        if error:
            return error
        if parsed is None:
            return f"查無 {label} 的三大法人期貨/選擇權分計資料，日期區間可能超出資料保存範圍（約近 3 年內）"

        rows = parsed[1]
        total = len(rows)
        shown, cap_note = cap_rows(rows, MAX_OUTPUT_ROWS, "請縮小 start_date～end_date")
        lines = [f"【三大法人期貨/選擇權分計】{label}（共 {total} 筆{cap_note}）\n"]
        for r in shown:
            # 偶數 index = 期貨欄位, 奇數 index = 選擇權欄位：
            # 多方交易口數[2,3] 多方契約金額[4,5] 空方口數[6,7] 空方金額[8,9] 淨口數[10,11] 淨金額[12,13]
            # 多方未平倉口數[14,15] 多方未平倉金額[16,17] 空方未平倉[18,19] 空方未平倉金額[20,21]
            # 淨未平倉口數[22,23] 淨未平倉金額[24,25]
            date, identity = r[0], r[1]
            lines.append(
                f"{date} | {identity}\n"
                f"  期貨: 交易 多{r[2]}/空{r[6]}/淨{r[10]}（淨額 {r[12]} 千元）| "
                f"未平倉 多{r[14]}/空{r[18]}/淨{r[22]}（淨額 {r[24]} 千元）\n"
                f"  選擇權: 交易 多{r[3]}/空{r[7]}/淨{r[11]}（淨額 {r[13]} 千元）| "
                f"未平倉 多{r[15]}/空{r[19]}/淨{r[23]}（淨額 {r[25]} 千元）"
            )
        return "\n".join(lines)
