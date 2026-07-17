"""TAIFEX futures daily OHLC history (multi-day download, not exposed via openapi.taifex.com.tw).

Also home to the shared helpers for parsing/decoding www.taifex.com.tw's HTML-form CSV
download responses, reused by institutional_futures_history.py — the same pattern as
TAIFEX_HEADERS living in futures_position.py and being imported by sibling modules.
"""

import csv
import io
from datetime import datetime
from typing import List, Optional, Tuple
from fastmcp import FastMCP
from utils import TWSEAPIClient, handle_api_errors
from .futures_position import TAIFEX_HEADERS

# www.taifex.com.tw's HTML-form download endpoint — distinct from openapi.taifex.com.tw's
# DailyMarketReportFut, which only ever returns the latest trading day with no date param.
# Confirmed by live testing: this endpoint accepts an arbitrary date range (max ~1 month per
# call, enforced client-side here since the server silently returns an empty/invalid body
# instead of an error when exceeded) and returns real historical OHLC per contract month.
FUT_DATA_DOWN_URL = "https://www.taifex.com.tw/cht/3/futDataDown"

MAX_SPAN_DAYS = 31


def parse_yyyymmdd(value: str) -> datetime:
    return datetime.strptime(value, "%Y%m%d")


def decode_and_parse_csv(body: bytes) -> Optional[Tuple[List[str], List[List[str]]]]:
    """Decode a Big5 CSV response body from a www.taifex.com.tw download endpoint.

    These endpoints return an HTML alert page (not an HTTP error status) when the query is
    rejected (bad/out-of-range dates), so that case is detected here and signaled as None
    rather than surfaced as parsed rows. Returns (header, data_rows) on success.
    """
    text = body.decode("big5", errors="replace")
    if "DateTime error" in text or text.lstrip().lower().startswith("<html"):
        return None

    rows = list(csv.reader(io.StringIO(text)))
    if len(rows) < 2:
        return None

    header, data_rows = rows[0], rows[1:]
    data_rows = [r for r in data_rows if len(r) >= len(header) and r[0].strip()]
    if not data_rows:
        return None

    return header, data_rows


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    """Register TAIFEX futures daily OHLC history tools."""
    _client = client or TWSEAPIClient.get_instance()

    @mcp.tool
    @handle_api_errors()
    def get_futures_daily_history(start_date: str, end_date: str, contract: str = "TX") -> str:
        """查詢期貨每日OHLC歷史行情（可回溯查詢，非僅最新一日）。
        資料來源為期交所網站下載頁面（www.taifex.com.tw），非 openapi.taifex.com.tw
        （openapi 版的 get_daily_futures_market_report 僅能查最新一個交易日，無法回溯）。
        實測資料至少可回溯至 2020 年。

        Args:
            start_date: 起始日期，格式 YYYYMMDD，例如 "20260601"
            end_date: 結束日期，格式 YYYYMMDD。與 start_date 區間不可超過一個月
            contract: 期貨契約代碼，預設 TX（臺股期貨）。其他常用：MTX（小型臺指）、
                TE（電子期貨）、TF（金融期貨）。與 get_institutional_traders_by_futures_history
                的契約代碼（TXF/EXF/FXF...）為不同代碼系統，不可混用

        Returns:
            區間內每個交易日、每個到期月份、一般與盤後時段的開高低收、成交量、未平倉資訊
        """
        try:
            start_dt = parse_yyyymmdd(start_date)
            end_dt = parse_yyyymmdd(end_date)
        except ValueError:
            return f"日期格式錯誤，請使用 YYYYMMDD 格式（例如 20260601），收到：start_date={start_date}, end_date={end_date}"

        if start_dt > end_dt:
            return f"起始日期 {start_date} 不可晚於結束日期 {end_date}"
        if (end_dt - start_dt).days > MAX_SPAN_DAYS:
            return f"查詢區間不可超過一個月（收到 {(end_dt - start_dt).days} 天），請縮小 start_date～end_date 範圍後重試"

        contract = contract.strip().upper()
        body = _client.fetch_bytes(
            FUT_DATA_DOWN_URL,
            method="POST",
            headers=TAIFEX_HEADERS,
            data={
                "down_type": "1",
                "commodity_id": contract,
                "commodity_id2": "",
                "queryStartDate": start_dt.strftime("%Y/%m/%d"),
                "queryEndDate": end_dt.strftime("%Y/%m/%d"),
            },
        )
        parsed = decode_and_parse_csv(body)
        if parsed is None:
            return f"查無契約 {contract} 在 {start_date}～{end_date} 的行情資料，請確認契約代碼是否正確、日期區間是否為交易日"

        _header, data_rows = parsed
        lines = [f"【期貨每日OHLC歷史行情】契約:{contract} 區間:{start_date}~{end_date}（共 {len(data_rows)} 筆）\n"]
        for r in data_rows:
            date, _contract, month, o, h, l, c = r[0], r[1], r[2].strip(), r[3], r[4], r[5], r[6]
            change, pct, vol, settle, oi, session = r[7], r[8], r[9], r[10], r[11], r[17]
            lines.append(
                f"{date} | {month} | {session} | 開:{o} 高:{h} 低:{l} 收:{c} | "
                f"漲跌:{change}({pct}) | 量:{vol} | 結算:{settle} | 未平倉:{oi}"
            )

        return "\n".join(lines)
