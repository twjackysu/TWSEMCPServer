"""TAIFEX 台指選擇權 Put/Call Ratio history (multi-day download, not exposed via openapi.taifex.com.tw)."""

from typing import Optional
from fastmcp import FastMCP
from utils import TWSEAPIClient, handle_api_errors
from .futures_position import TAIFEX_HEADERS
from .futures_daily_history import parse_yyyymmdd, decode_and_parse_csv

# openapi.taifex.com.tw's PutCallRatio endpoint (get_put_call_ratio) already returns a
# rolling ~21-trading-day window with no date param. This endpoint (www.taifex.com.tw's
# download page) genuinely accepts an arbitrary start/end date, useful for pulling a
# specific past period rather than only "recent". Server-enforced max span: 30 calendar days.
PC_RATIO_DOWN_URL = "https://www.taifex.com.tw/cht/3/pcRatioDown"

MAX_SPAN_DAYS = 30


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    """Register TAIFEX Put/Call Ratio history tools."""
    _client = client or TWSEAPIClient.get_instance()

    @mcp.tool
    @handle_api_errors()
    def get_put_call_ratio_history(start_date: str, end_date: str) -> str:
        """查詢台指選擇權 Put/Call Ratio 歷史資料（可指定任意起訖區間，非僅近期滾動窗口）。
        與 get_put_call_ratio（openapi 版，固定回傳近 21 個交易日）不同，此工具可指定任意
        過去起訖日期，適合回溯特定歷史期間的市場多空氣氛。

        Args:
            start_date: 起始日期，格式 YYYYMMDD，例如 "20260501"
            end_date: 結束日期，格式 YYYYMMDD。與 start_date 區間不可超過 30 天

        Returns:
            區間內每個交易日的賣權/買權成交量、買賣權成交量比率%、賣權/買權未平倉量、買賣權未平倉量比率%
        """
        try:
            start_dt = parse_yyyymmdd(start_date)
            end_dt = parse_yyyymmdd(end_date)
        except ValueError:
            return f"日期格式錯誤，請使用 YYYYMMDD 格式（例如 20260501），收到：start_date={start_date}, end_date={end_date}"

        if start_dt > end_dt:
            return f"起始日期 {start_date} 不可晚於結束日期 {end_date}"
        if (end_dt - start_dt).days > MAX_SPAN_DAYS:
            return f"查詢區間不可超過 {MAX_SPAN_DAYS} 天（收到 {(end_dt - start_dt).days} 天），請縮小 start_date～end_date 範圍後重試"

        body = _client.fetch_bytes(
            PC_RATIO_DOWN_URL,
            method="POST",
            headers=TAIFEX_HEADERS,
            data={
                "queryStartDate": start_dt.strftime("%Y/%m/%d"),
                "queryEndDate": end_dt.strftime("%Y/%m/%d"),
            },
        )
        parsed = decode_and_parse_csv(body)
        if parsed is None:
            return f"查無 {start_date}～{end_date} 的 Put/Call Ratio 資料，日期區間可能無效或超出範圍"

        _header, data_rows = parsed
        lines = [f"【台指選擇權 Put/Call Ratio 歷史】區間:{start_date}~{end_date}（共 {len(data_rows)} 筆）\n"]
        for r in data_rows:
            date, put_vol, call_vol, pcr_vol, put_oi, call_oi, pcr_oi = r[0], r[1], r[2], r[3], r[4], r[5], r[6]
            lines.append(
                f"{date} | 成交量 PCR:{pcr_vol}%（Put:{put_vol} Call:{call_vol}） | "
                f"未平倉 PCR:{pcr_oi}%（Put:{put_oi} Call:{call_oi}）"
            )

        return "\n".join(lines)
