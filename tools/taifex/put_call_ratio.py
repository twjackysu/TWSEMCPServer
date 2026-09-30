"""TAIFEX 台指選擇權 Put/Call Ratio, recent window or any past period.

Source: www.taifex.com.tw download page pcRatioDown. Replaces the openapi PutCallRatio
tool, whose rolling ~20-trading-day window matched this endpoint row for row on 2026-09-29
but could not reach further back.
"""

from datetime import timedelta
from typing import Optional
from fastmcp import FastMCP
from utils import TWSEAPIClient, handle_api_errors
from utils.taifex import (
    TAIFEX_DOWNLOAD_BASE,
    TAIFEX_HEADERS,
    decode_and_parse_csv,
    download_form,
    parse_date_range,
    taipei_today,
)

PC_RATIO_DOWN_URL = f"{TAIFEX_DOWNLOAD_BASE}/pcRatioDown"
# Server-enforced max span: 30 calendar days.
MAX_SPAN_DAYS = 30


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    """Register TAIFEX put/call ratio tools."""
    _client = client or TWSEAPIClient.get_instance()

    @mcp.tool
    @handle_api_errors()
    def get_put_call_ratio(start_date: str = "", end_date: str = "") -> str:
        """查詢台指選擇權 Put/Call Ratio，衡量市場恐慌與樂觀程度的情緒指標：預設近 30 天，
        也可指定任意過去區間。PCR > 1.5 通常視為過度悲觀，< 0.5 通常視為過度樂觀。

        Args:
            start_date: 起始日期，格式 YYYYMMDD，例如 "20260501"（選填，留空＝近 30 天）
            end_date: 結束日期，格式 YYYYMMDD（選填，預設同 start_date）。區間不可超過 30 天

        Returns:
            每個交易日的成交量 PCR、未平倉量 PCR，以及 put/call 各自的成交量與未平倉量
        """
        if not start_date and not end_date:
            end_dt = taipei_today()
            start_dt = end_dt - timedelta(days=MAX_SPAN_DAYS)
            label = "近 30 天"
        else:
            start_date, end_date = start_date or end_date, end_date or start_date
            start_dt, end_dt, error = parse_date_range(start_date, end_date, MAX_SPAN_DAYS, "20260501")
            if error:
                return error
            label = f"{start_date}～{end_date}"

        body = _client.fetch_bytes(
            PC_RATIO_DOWN_URL,
            method="POST",
            headers=TAIFEX_HEADERS,
            data=download_form(start_dt, end_dt),
        )
        parsed = decode_and_parse_csv(body)
        if parsed is None:
            return f"查無 {label} 的 Put/Call Ratio 資料，日期區間可能無效或超出範圍"

        _header, data_rows = parsed
        lines = [f"【台指選擇權 Put/Call Ratio】{label}（共 {len(data_rows)} 個交易日）\n"]
        for r in data_rows:
            # r: 日期,賣權成交量,買權成交量,買賣權成交量比率%,賣權未平倉量,買權未平倉量,買賣權未平倉量比率%
            date, put_vol, call_vol, pcr_vol, put_oi, call_oi, pcr_oi = r[0], r[1], r[2], r[3], r[4], r[5], r[6]
            lines.append(
                f"{date} | 成交量 PCR:{pcr_vol}%（Put:{put_vol} Call:{call_vol}） | "
                f"未平倉 PCR:{pcr_oi}%（Put:{put_oi} Call:{call_oi}）"
            )
        return "\n".join(lines)
