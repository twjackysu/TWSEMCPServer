"""TAIFEX 選擇權每日OHLC歷史行情 history (multi-day download, not exposed via openapi.taifex.com.tw)."""

from typing import Optional
from fastmcp import FastMCP
from utils import TWSEAPIClient, handle_api_errors
from .futures_position import TAIFEX_HEADERS
from .futures_daily_history import parse_yyyymmdd, decode_and_parse_csv

# openapi.taifex.com.tw's DailyMarketReportOpt (get_daily_options_market_report) only
# returns the latest trading day. This endpoint (www.taifex.com.tw download page)
# accepts an arbitrary date range up to ~1 month (server-enforced, same as futDataDown).
# `commodity_id` DOES filter server-side (confirmed live: TXO-only request returns only
# TXO rows) — but even a single day for TXO alone is ~6,400 rows across all strikes and
# ~9 contract months, so a multi-day pull without a contract_month filter would be far
# too large for tool output. If contract_month is omitted and the result is large, the
# available months are listed instead of dumping everything (same UX as get_options_delta).
OPT_DATA_DOWN_URL = "https://www.taifex.com.tw/cht/3/optDataDown"

MAX_SPAN_DAYS = 31
ROW_LIMIT_WITHOUT_MONTH_FILTER = 300


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    """Register TAIFEX options daily OHLC history tools."""
    _client = client or TWSEAPIClient.get_instance()

    @mcp.tool
    @handle_api_errors()
    def get_options_daily_history(start_date: str, end_date: str, contract: str = "TXO",
                                   contract_month: str = "", call_put: str = "") -> str:
        """查詢選擇權每日OHLC歷史行情（可回溯查詢，非僅最新一日）。
        與 get_daily_options_market_report（openapi 版，僅能查最新一個交易日）不同，此工具
        可查詢任意過去起訖日期。因資料量龐大（單日單契約逾6000筆，涵蓋全部履約價與到期月份），
        強烈建議指定 contract_month 縮小範圍；若未指定且資料量過大，會改為列出可用到期月份。

        Args:
            start_date: 起始日期，格式 YYYYMMDD，例如 "20260601"
            end_date: 結束日期，格式 YYYYMMDD。與 start_date 區間不可超過一個月
            contract: 選擇權契約代碼，預設 TXO（臺指選擇權）。其他常用：TEO（電子選擇權）、
                TFO（金融選擇權）
            contract_month: 到期月份/週次，例如「202606」或「202606W1」。留空且資料量過大時，
                會回傳可用到期月份清單供選擇
            call_put: 篩選「買權」或「賣權」，留空則顯示全部

        Returns:
            區間內每個交易日、指定到期月份各履約價的開高低收、成交量、結算價、未沖銷契約數
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
            OPT_DATA_DOWN_URL,
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
            return f"查無契約 {contract} 在 {start_date}～{end_date} 的選擇權行情資料，請確認契約代碼是否正確"

        _header, data_rows = parsed

        if contract_month:
            data_rows = [r for r in data_rows if r[2].strip() == contract_month]
        if call_put:
            data_rows = [r for r in data_rows if r[4] == call_put]

        if not contract_month and len(data_rows) > ROW_LIMIT_WITHOUT_MONTH_FILTER:
            months = sorted(set(r[2].strip() for r in data_rows))
            return (
                f"契約 {contract} 在 {start_date}～{end_date} 共有 {len(data_rows)} 筆資料，"
                f"資料量過大無法完整顯示。可用到期月份（共 {len(months)} 個）：\n"
                + "、".join(months)
                + "\n請指定 contract_month 參數以縮小查詢範圍。"
            )

        if not data_rows:
            return f"查無契約 {contract} 在 {start_date}～{end_date}（到期月份:{contract_month or '全部'}）的選擇權行情資料"

        lines = [
            f"【選擇權每日OHLC歷史行情】契約:{contract} 到期月份:{contract_month or '全部'} "
            f"區間:{start_date}~{end_date}（共 {len(data_rows)} 筆）\n"
        ]
        for r in data_rows:
            date, month, strike, cp = r[0], r[2].strip(), r[3], r[4]
            o, h, l, c = r[5], r[6], r[7], r[8]
            vol, settle, oi, session = r[9], r[10], r[11], r[17]
            lines.append(
                f"{date} | {month} | 履約價:{strike} {cp} | {session} | "
                f"開:{o} 高:{h} 低:{l} 收:{c} | 量:{vol} | 結算:{settle} | 未平倉:{oi}"
            )

        return "\n".join(lines)
