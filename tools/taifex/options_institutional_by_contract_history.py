"""TAIFEX 三大法人各選擇權契約 history (multi-day download, aggregated across CALL+PUT)."""

from typing import Optional
from fastmcp import FastMCP
from utils import TWSEAPIClient, handle_api_errors
from .futures_position import TAIFEX_HEADERS
from .futures_daily_history import parse_yyyymmdd, decode_and_parse_csv

# Distinct from get_options_institutional_calls_puts_history: that tool splits CALL vs
# PUT; this endpoint (optContractsDateDown) reports each contract's totals with CALL and
# PUT combined. openapi.taifex.com.tw's get_institutional_traders_by_options only returns
# the latest trading day; this download-page endpoint accepts an arbitrary date range. No
# server-enforced span cap observed (tested a clean 3-month pull), capped client-side at
# 92 days. Retention verified to run out between 2023/06 and 2023/09.
OPT_CONTRACTS_DATE_DOWN_URL = "https://www.taifex.com.tw/cht/3/optContractsDateDown"

MAX_SPAN_DAYS = 92


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    """Register TAIFEX institutional options-by-contract history tools."""
    _client = client or TWSEAPIClient.get_instance()

    @mcp.tool
    @handle_api_errors()
    def get_options_institutional_by_contract_history(start_date: str, end_date: str, contract: str = "TXO") -> str:
        """查詢三大法人各選擇權契約交易歷史（CALL+PUT合計，可回溯查詢，非僅最新一日）。
        與 get_options_institutional_calls_puts_history（同樣可回溯，但拆分 CALL/PUT）不同，
        此工具回傳的是該選擇權契約 CALL 與 PUT 合計後的總數。
        與 get_institutional_traders_by_options（openapi 版，僅能查最新一個交易日）不同，
        此工具可查詢任意過去起訖日期。

        Args:
            start_date: 起始日期，格式 YYYYMMDD，例如 "20260401"
            end_date: 結束日期，格式 YYYYMMDD。與 start_date 區間不可超過 92 天
            contract: 選擇權契約代碼，預設 TXO（臺指選擇權）。其他常用：TEO（電子選擇權）、
                TFO（金融選擇權）

        Returns:
            區間內每個交易日、每個身份別（自營商/投信/外資）在該契約的CALL+PUT合計多空交易口數、
            契約金額、未平倉資訊
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

        contract = contract.strip().upper()
        body = _client.fetch_bytes(
            OPT_CONTRACTS_DATE_DOWN_URL,
            method="POST",
            headers=TAIFEX_HEADERS,
            data={
                "queryStartDate": start_dt.strftime("%Y/%m/%d"),
                "queryEndDate": end_dt.strftime("%Y/%m/%d"),
                "commodityId": contract,
            },
        )
        parsed = decode_and_parse_csv(body)
        if parsed is None:
            return (
                f"查無契約 {contract} 在 {start_date}～{end_date} 的三大法人選擇權契約資料，"
                f"請確認契約代碼是否正確；日期區間也可能超出資料保存範圍（約近 3 年內）"
            )

        _header, data_rows = parsed
        lines = [
            f"【三大法人選擇權契約歷史（CALL+PUT合計）】契約:{contract} 區間:{start_date}~{end_date}（共 {len(data_rows)} 筆）\n"
        ]
        for r in data_rows:
            date, name, identity = r[0], r[1], r[2]
            long_vol, long_amt = r[3], r[4]
            short_vol, short_amt = r[5], r[6]
            net_vol, net_amt = r[7], r[8]
            oi_long, oi_short, oi_net = r[9], r[11], r[13]
            lines.append(
                f"{date} | {name} | {identity}\n"
                f"  交易: 多 {long_vol}({long_amt}千元) / 空 {short_vol}({short_amt}千元) / 淨 {net_vol}({net_amt}千元)\n"
                f"  未平倉: 多 {oi_long} / 空 {oi_short} / 淨 {oi_net}"
            )

        return "\n".join(lines)
