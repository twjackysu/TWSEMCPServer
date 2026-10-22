"""Valuation ratios (P/E, dividend yield, P/B) of listed stocks, latest or any past date.

Replaces the OpenAPI /exchangeReport/BWIBBU_ALL and /exchangeReport/BWIBBU_d tools: both
only served the latest day, and on 2026-09-29 carried exactly the same 1083 stocks and
values as this endpoint, which also has 股利年度 and 財報年/季.
"""

from typing import Optional
from fastmcp import FastMCP
from utils import TWSEAPIClient, DEFAULT_DISPLAY_LIMIT, Page, printed
from toolkit import Limit, Offset, TradingDate, handle_api_errors
from sources.twse.bwibbu_d import valuation_ratios


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    """Register market valuation tools."""
    _client = client or TWSEAPIClient.get_instance()

    @mcp.tool
    @handle_api_errors()
    def get_stock_valuation_ratios(date: TradingDate = "", stock_no: str = "", name: str = "",
                                   limit: Limit = DEFAULT_DISPLAY_LIMIT, offset: Offset = 0) -> str:
        """查詢上市股票本益比（P/E、PER）、殖利率、股價淨值比（P/B、PBR）：預設最新交易日，也可指定過去日期。
        可查單一個股，或全市場清單用於篩選低估值個股、比較產業估值水位。

        回傳：每支股票的代號、名稱、收盤價、本益比、殖利率(%)、股利年度、股價淨值比、財報年/季

        Args:
            date: 查詢日期 西元 YYYYMMDD（選填，留空＝最新交易日）
            stock_no: 股票代號（選填），指定則只回傳該股票
            name: 股票名稱關鍵字（選填）
            limit: 回傳筆數上限（預設 50）。全市場逾 1000 檔，未分頁的完整輸出逾 60KB
            offset: 跳過前 N 筆（預設 0，搭配 limit 分頁）
        """
        report = valuation_ratios(_client, date)
        label = date or "最新交易日"
        if not report.found:
            reason = report.stat or "請確認該日期為交易日（非假日或週末）"
            return f"查無 {label} 的估值資料：{reason}"

        # The endpoint echoes back the date it actually served. Never relabel a
        # different day's data with the requested date.
        served_date = report.date or date
        if date and served_date != date:
            return (
                f"查無 {date} 的估值資料，來源實際回傳的是 {served_date} 的資料，"
                f"請改用 {served_date} 查詢，或確認 {date} 為交易日。"
            )

        data = report.valuations
        if not data:
            return f"查無 {label} 的估值資料"

        if stock_no:
            data = [v for v in data if v.code == stock_no.strip()]
            if not data:
                return f"查無股票代號 {stock_no} 在 {served_date} 的估值資料"
        if name:
            data = [v for v in data if name in v.name]
            if not data:
                return f"查無名稱包含「{name}」的股票在 {served_date} 的估值資料"

        paged = Page(limit, offset).take(data)
        if paged.past_end:
            return paged.out_of_range(f"{served_date} 的估值資料")

        title = report.title or f"全市場估值資料 - {served_date}"
        span = f"，{paged.span()}" if paged.span() else ""
        lines = [f"【{title}】（共 {paged.total} 筆{span}）\n"]
        for v in paged.rows:
            lines.append(
                f"{v.code} {v.name} | 收盤價: {printed(v.close, '-')} | 本益比: {printed(v.pe, '-')} | "
                f"殖利率: {printed(v.dividend_yield, '-')}%（股利年度 {v.dividend_year or '-'}）| "
                f"股價淨值比: {printed(v.pb, '-')}（財報 {v.fiscal or '-'}）"
            )

        if paged.more():
            lines.append("\n" + paged.more())
        return "\n".join(lines)
