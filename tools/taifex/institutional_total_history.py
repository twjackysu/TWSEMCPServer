"""TAIFEX 三大法人期貨+選擇權總表 history (multi-day download)."""

from typing import Optional
from fastmcp import FastMCP
from utils import TWSEAPIClient, handle_api_errors
from .futures_position import TAIFEX_HEADERS
from .futures_daily_history import parse_yyyymmdd, decode_and_parse_csv

# openapi.taifex.com.tw's get_institutional_general only returns the latest trading day.
# This endpoint (www.taifex.com.tw download page) accepts an arbitrary date range. No
# server-enforced span cap observed (tested a clean 3-month pull), capped client-side at
# 92 days to bound tool output. Retention verified to run out between 2023/06 and 2023/09,
# matching the other TAIFEX history tools built on this same download-page family.
TOTAL_TABLE_DATE_DOWN_URL = "https://www.taifex.com.tw/cht/3/totalTableDateDown"

MAX_SPAN_DAYS = 92


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    """Register TAIFEX institutional futures+options total table history tools."""
    _client = client or TWSEAPIClient.get_instance()

    @mcp.tool
    @handle_api_errors()
    def get_institutional_total_history(start_date: str, end_date: str) -> str:
        """查詢三大法人期貨與選擇權合計總表歷史（可回溯查詢，非僅最新一日）。
        與 get_institutional_general（openapi 版，僅能查最新一個交易日）不同，此工具可查詢
        任意過去起訖日期。與 get_institutional_traders_by_futures_history（僅期貨）不同，
        此工具是期貨+選擇權合計數字。

        Args:
            start_date: 起始日期，格式 YYYYMMDD，例如 "20260401"
            end_date: 結束日期，格式 YYYYMMDD。與 start_date 區間不可超過 92 天

        Returns:
            區間內每個交易日、每個身份別（自營商/投信/外資及陸資）的期貨+選擇權合計多空交易口數、
            契約金額（百萬元）、未平倉資訊
        """
        try:
            start_dt = parse_yyyymmdd(start_date)
            end_dt = parse_yyyymmdd(end_date)
        except ValueError:
            return f"日期格式錯誤，請使用 YYYYMMDD 格式（例如 20260401），收到：start_date={start_date}, end_date={end_date}"

        if start_dt > end_dt:
            return f"起始日期 {start_date} 不可晚於結束日期 {end_date}"
        if (end_dt - start_dt).days > MAX_SPAN_DAYS:
            return f"查詢區間不可超過 {MAX_SPAN_DAYS} 天（收到 {(end_dt - start_dt).days} 天），請縮小 start_date～end_date 範圍後重試"

        body = _client.fetch_bytes(
            TOTAL_TABLE_DATE_DOWN_URL,
            method="POST",
            headers=TAIFEX_HEADERS,
            data={
                "queryStartDate": start_dt.strftime("%Y/%m/%d"),
                "queryEndDate": end_dt.strftime("%Y/%m/%d"),
            },
        )
        parsed = decode_and_parse_csv(body)
        if parsed is None:
            return (
                f"查無 {start_date}～{end_date} 的三大法人期貨+選擇權總表資料，"
                f"日期區間可能超出資料保存範圍（約近 3 年內）或格式有誤"
            )

        _header, data_rows = parsed
        lines = [f"【三大法人期貨+選擇權總表歷史】區間:{start_date}~{end_date}（共 {len(data_rows)} 筆）\n"]
        for r in data_rows:
            date, identity = r[0], r[1]
            long_vol, long_amt = r[2], r[3]
            short_vol, short_amt = r[4], r[5]
            net_vol, net_amt = r[6], r[7]
            oi_long, oi_short, oi_net = r[8], r[10], r[12]
            lines.append(
                f"{date} | {identity}\n"
                f"  交易: 多 {long_vol}({long_amt}百萬元) / 空 {short_vol}({short_amt}百萬元) / 淨 {net_vol}({net_amt}百萬元)\n"
                f"  未平倉: 多 {oi_long} / 空 {oi_short} / 淨 {oi_net}"
            )

        return "\n".join(lines)
