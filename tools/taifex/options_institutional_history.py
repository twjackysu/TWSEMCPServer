"""TAIFEX 三大法人選擇權 CALL/PUT 分計 history (multi-day download)."""

from typing import Optional
from fastmcp import FastMCP
from utils import TWSEAPIClient, handle_api_errors
from .futures_position import TAIFEX_HEADERS
from .futures_daily_history import parse_yyyymmdd, decode_and_parse_csv

# openapi.taifex.com.tw's get_institutional_traders_calls_puts only returns the latest
# trading day. This endpoint (www.taifex.com.tw download page) accepts an arbitrary date
# range. No server-enforced span cap observed (tested a clean 90-day pull), but capped
# client-side to keep tool output manageable. Retention verified back to roughly 2023H2.
CALLS_AND_PUTS_DATE_DOWN_URL = "https://www.taifex.com.tw/cht/3/callsAndPutsDateDown"

MAX_SPAN_DAYS = 92


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    """Register TAIFEX institutional options calls/puts history tools."""
    _client = client or TWSEAPIClient.get_instance()

    @mcp.tool
    @handle_api_errors()
    def get_options_institutional_calls_puts_history(start_date: str, end_date: str, contract: str = "TXO") -> str:
        """查詢三大法人選擇權買賣權（CALL/PUT）分計交易歷史（可回溯查詢，非僅最新一日）。
        與 get_institutional_traders_calls_puts（openapi 版，僅能查最新一個交易日）不同，
        此工具可查詢任意過去起訖日期，適合觀察外資對選擇權 CALL/PUT 布局隨時間的變化趨勢。

        Args:
            start_date: 起始日期，格式 YYYYMMDD，例如 "20260401"
            end_date: 結束日期，格式 YYYYMMDD。與 start_date 區間不可超過 92 天
            contract: 選擇權契約代碼，預設 TXO（臺指選擇權）。其他常用：TEO（電子選擇權）、
                TFO（金融選擇權）

        Returns:
            區間內每個交易日、每個身份別（自營商/投信/外資）在 CALL/PUT 的買賣口數、契約金額、未平倉資訊
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
            CALLS_AND_PUTS_DATE_DOWN_URL,
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
                f"查無契約 {contract} 在 {start_date}～{end_date} 的三大法人買賣權分計資料，"
                f"請確認契約代碼是否正確；日期區間也可能超出資料保存範圍（約近 3 年內）"
            )

        _header, data_rows = parsed
        lines = [
            f"【三大法人選擇權買賣權分計歷史】契約:{contract} 區間:{start_date}~{end_date}（共 {len(data_rows)} 筆）\n"
        ]
        for r in data_rows:
            date, name, cp, identity = r[0], r[1], r[2], r[3]
            buy_vol, buy_amt = r[4], r[5]
            sell_vol, sell_amt = r[6], r[7]
            net_vol, net_amt = r[8], r[9]
            oi_buy, oi_sell, oi_net = r[10], r[12], r[14]
            lines.append(
                f"{date} | {name} {cp} | {identity}\n"
                f"  交易: 買 {buy_vol}({buy_amt}千元) / 賣 {sell_vol}({sell_amt}千元) / 淨 {net_vol}({net_amt}千元)\n"
                f"  未平倉: 買 {oi_buy} / 賣 {oi_sell} / 淨 {oi_net}"
            )

        return "\n".join(lines)
