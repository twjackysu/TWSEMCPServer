"""TAIFEX 三大法人 futures position history by contract, by date (multi-day download).

Distinct data source from tools/taifex/institutional_details.py's get_institutional_traders_by_futures,
which hits openapi.taifex.com.tw and only ever returns the latest trading day. This module scrapes
www.taifex.com.tw's HTML-form download endpoint, which genuinely accepts an arbitrary date range.
"""

from typing import Optional
from fastmcp import FastMCP
from utils import TWSEAPIClient, handle_api_errors
from .futures_position import TAIFEX_HEADERS
from .futures_daily_history import parse_yyyymmdd, decode_and_parse_csv

FUT_CONTRACTS_DATE_DOWN_URL = "https://www.taifex.com.tw/cht/3/futContractsDateDown"

# Server does not enforce a hard span cap (tested 6 months successfully), but responses grow
# ~3 rows/trading-day/contract (dealer/investment trust/foreign), so cap client-side to keep
# tool output manageable.
MAX_SPAN_DAYS = 92


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    """Register TAIFEX institutional futures position history tools."""
    _client = client or TWSEAPIClient.get_instance()

    @mcp.tool
    @handle_api_errors()
    def get_institutional_traders_by_futures_history(start_date: str, end_date: str, contract: str = "TXF") -> str:
        """查詢三大法人期貨部位歷史資料（可回溯查詢，非僅最新一日）。
        資料來源為期交所網站下載頁面（www.taifex.com.tw），非 openapi.taifex.com.tw
        （openapi 版的 get_institutional_traders_by_futures 僅能查最新一個交易日，無法回溯）。
        實測資料約可回溯至 2023 年下半年（更早日期會查詢失敗），區間不可超過 3 個月。

        Args:
            start_date: 起始日期，格式 YYYYMMDD，例如 "20260601"
            end_date: 結束日期，格式 YYYYMMDD。與 start_date 區間不可超過 92 天
            contract: 期貨契約代碼，預設 TXF（臺股期貨）。留空則查詢全部契約（資料量較大）。
                其他常用：MXF（小型臺指）、EXF（電子期貨）、FXF（金融期貨）、TMF（微型臺指）。
                與 get_futures_daily_history 的契約代碼（TX/MTX/TE/TF...）為不同代碼系統，不可混用

        Returns:
            區間內每個交易日、自營商/投信/外資及陸資的多空交易口數、契約金額、未平倉資訊
        """
        try:
            start_dt = parse_yyyymmdd(start_date)
            end_dt = parse_yyyymmdd(end_date)
        except ValueError:
            return f"日期格式錯誤，請使用 YYYYMMDD 格式（例如 20260601），收到：start_date={start_date}, end_date={end_date}"

        if start_dt > end_dt:
            return f"起始日期 {start_date} 不可晚於結束日期 {end_date}"
        if (end_dt - start_dt).days > MAX_SPAN_DAYS:
            return f"查詢區間不可超過 {MAX_SPAN_DAYS} 天（收到 {(end_dt - start_dt).days} 天），請縮小 start_date～end_date 範圍後重試"

        contract = contract.strip().upper()
        body = _client.fetch_bytes(
            FUT_CONTRACTS_DATE_DOWN_URL,
            method="POST",
            headers=TAIFEX_HEADERS,
            data={
                "queryStartDate": start_dt.strftime("%Y/%m/%d"),
                "queryEndDate": end_dt.strftime("%Y/%m/%d"),
                "commodityId": contract,
            },
        )
        parsed = decode_and_parse_csv(body)
        contract_label = contract or "全部契約"
        if parsed is None:
            return (
                f"查無契約 {contract_label} 在 {start_date}～{end_date} 的三大法人資料，"
                f"請確認契約代碼是否正確；日期區間也可能超出資料保存範圍（約近 3 年內）"
            )

        _header, data_rows = parsed
        lines = [
            f"【三大法人期貨部位歷史】契約:{contract_label} 區間:{start_date}~{end_date}（共 {len(data_rows)} 筆）\n"
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
