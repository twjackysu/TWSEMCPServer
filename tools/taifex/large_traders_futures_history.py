"""TAIFEX 大額交易人期貨未沖銷部位 history (multi-day download, client-side filtered by contract)."""

from typing import Optional
from fastmcp import FastMCP
from utils import TWSEAPIClient, handle_api_errors
from .futures_position import TAIFEX_HEADERS
from .futures_daily_history import parse_yyyymmdd, decode_and_parse_csv

# openapi.taifex.com.tw's get_large_traders_futures_oi only returns the latest trading
# day. This endpoint (www.taifex.com.tw download page) accepts an arbitrary date range,
# but — unlike futDataDown/futContractsDateDown — the form has NO contract-code filter
# field at all (confirmed by inspecting the live form and its submit handler): every
# call returns ALL ~340 commodities for the requested dates (~1,100 rows/day), so
# filtering to one contract must happen client-side after the fetch. Because the raw
# payload size doesn't shrink with a narrower contract, span is capped tightly here.
LARGE_TRADER_FUT_DOWN_URL = "https://www.taifex.com.tw/cht/3/largeTraderFutDown"

MAX_SPAN_DAYS = 31


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    """Register TAIFEX large-trader futures OI history tools."""
    _client = client or TWSEAPIClient.get_instance()

    @mcp.tool
    @handle_api_errors()
    def get_large_traders_futures_history(start_date: str, end_date: str, contract: str) -> str:
        """查詢期貨大額交易人未沖銷部位歷史資料（可回溯查詢，非僅最新一日）。
        與 get_large_traders_futures_oi（openapi 版，僅能查最新一個交易日）不同，此工具可
        查詢任意過去起訖日期。來源端點本身不支援依契約篩選（一次回傳全部約340種商品），
        故 contract 為必填參數，由本工具在取得資料後於本地端篩選。

        Args:
            start_date: 起始日期，格式 YYYYMMDD，例如 "20260601"
            end_date: 結束日期，格式 YYYYMMDD。與 start_date 區間不可超過一個月
            contract: 期貨契約代碼（必填），例如 "TX"（臺股期貨）、"MTX"（小型臺指）、
                "TE"（電子期貨）、"TF"（金融期貨）

        Returns:
            區間內每個交易日，該契約各到期月份的前五大／前十大交易人買方、賣方部位數與全市場未沖銷部位數
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
        if not contract or not contract.strip():
            return "contract 為必填參數，請指定期貨契約代碼（例如 TX、MTX、TE、TF）"

        contract = contract.strip().upper()
        body = _client.fetch_bytes(
            LARGE_TRADER_FUT_DOWN_URL,
            method="POST",
            headers=TAIFEX_HEADERS,
            data={
                "queryStartDate": start_dt.strftime("%Y/%m/%d"),
                "queryEndDate": end_dt.strftime("%Y/%m/%d"),
            },
        )
        parsed = decode_and_parse_csv(body)
        if parsed is None:
            return f"查無 {start_date}～{end_date} 的大額交易人未沖銷部位資料，日期區間可能無效或超出範圍"

        _header, data_rows = parsed
        data_rows = [r for r in data_rows if r[1].strip() == contract]
        if not data_rows:
            return f"查無契約 {contract} 在 {start_date}～{end_date} 的大額交易人未沖銷部位資料，請確認契約代碼是否正確"

        lines = [
            f"【期貨大額交易人未沖銷部位歷史】契約:{contract} 區間:{start_date}~{end_date}（共 {len(data_rows)} 筆）\n"
        ]
        for r in data_rows:
            date, month, category = r[0], r[3].strip(), r[4]
            top5_buy, top5_sell = r[5], r[6]
            top10_buy, top10_sell = r[7], r[8]
            market_oi = r[9]
            lines.append(
                f"{date} | {month} | 類別:{category} | "
                f"前五大: 買 {top5_buy} / 賣 {top5_sell} | 前十大: 買 {top10_buy} / 賣 {top10_sell} | "
                f"全市場未平倉: {market_oi}"
            )

        return "\n".join(lines)
