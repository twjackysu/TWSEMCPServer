"""Foreign/mainland-China (外資及陸資) shareholding of every listed stock, latest or any past date.

Replaces the OpenAPI /fund/MI_QFIIS_sort_20 tool (get_top_foreign_holdings): on 2026-09-29
its top 20 were exactly this endpoint's rows sorted by 全體外資及陸資持股比率, with the same
ratios, limits and share counts, and it could neither pick a date nor look up one stock.
Read through the MI_QFIIS gateway (``sources.twse.mi_qfiis``).
"""

from decimal import Decimal
from typing import Literal, Optional
from fastmcp import FastMCP
from sources.twse.mi_qfiis import ForeignHolding, foreign_holdings
from utils import TWSEAPIClient, DEFAULT_DISPLAY_LIMIT, format_list_response, printed
from toolkit import Limit, Offset, TradingDate, handle_api_errors

SortBy = Literal["code", "ratio"]
NO_RATIO = Decimal(-1)  # a missing 持股比率 sorts last


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    """Register TWSE foreign holdings tools."""
    _client = client or TWSEAPIClient.get_instance()

    @mcp.tool
    @handle_api_errors()
    def get_foreign_holdings(date: TradingDate = "", stock_no: str = "", name: str = "", sort_by: SortBy = "code",
                             limit: Limit = DEFAULT_DISPLAY_LIMIT, offset: Offset = 0) -> str:
        """查詢上市股票外資及陸資持股比率：預設最新交易日，也可指定任意過去日期，適合追蹤外資持股變化。
        sort_by="ratio" 可依外資持股比率由高到低排行（例如 limit=20 即外資持股前 20 名）。
        產業別匯總請用 get_foreign_investment_by_industry。

        回傳：每支股票的代號、名稱、全體外資及陸資持股比率、尚可投資比率、投資上限比率、持有股數、發行股數

        Args:
            date: 查詢日期，格式 西元 YYYYMMDD，例如 "20260610"（選填，留空＝最新交易日）
            stock_no: 股票代號（選填），指定則只回傳該股票
            name: 股票名稱關鍵字（選填）
            sort_by: "code"＝依證券代號（預設）；"ratio"＝依全體外資及陸資持股比率由高到低
            limit: 回傳筆數上限（預設 50）
            offset: 跳過前 N 筆（預設 0，搭配 limit 分頁）
        """
        label = date or "最新交易日"
        day = foreign_holdings(_client, date)
        if day is None:
            return f"查無 {label} 的外資及陸資持股資料，請確認該日期為交易日（非假日或週末）"

        data = day.holdings
        if not data:
            return f"查無 {label} 的外資及陸資持股資料"
        served = day.date or label

        if stock_no:
            data = [h for h in data if h.code == stock_no.strip()]
            if not data:
                return f"查無股票代號 {stock_no} 在 {served} 的外資及陸資持股資料"
        if name:
            data = [h for h in data if name in h.name]
            if not data:
                return f"查無名稱包含「{name}」的股票在 {served} 的外資及陸資持股資料"
        if sort_by == "ratio":
            data = sorted(data, key=lambda h: NO_RATIO if h.held_pct is None else h.held_pct, reverse=True)

        def fmt(h: ForeignHolding) -> str:
            return (
                f"{h.code} {h.name} | 外資持股比率:{printed(h.held_pct)}% | 尚可投資比率:{printed(h.available_pct)}% | "
                f"投資上限:{printed(h.limit_pct)}% | 持有股數:{printed(h.held_shares)} | "
                f"發行股數:{printed(h.issued_shares)}\n"
            )

        order = "，依持股比率由高到低" if sort_by == "ratio" else ""
        return format_list_response(data, f" {served} 上市股票外資及陸資持股{order}", fmt, limit, offset)
