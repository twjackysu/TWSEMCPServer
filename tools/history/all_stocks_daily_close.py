"""Daily quotes of every listed stock (whole-market snapshot), latest or any past date.

Replaces the OpenAPI /exchangeReport/STOCK_DAY_ALL tool: on 2026-09-29 it carried exactly
the same 1382 stocks and values as this endpoint's 每日收盤行情 table, which also has the
last bid/ask and P/E, and accepts past dates.
"""

from typing import Optional
from fastmcp import FastMCP
from utils import TWSEAPIClient, DEFAULT_DISPLAY_LIMIT, Page, printed
from toolkit import Limit, Offset, TradingDate, handle_api_errors
from sources.twse.mi_index import stock_quotes


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    """Register TWSE all-stocks daily close tools."""
    _client = client or TWSEAPIClient.get_instance()

    @mcp.tool
    @handle_api_errors()
    def get_stock_daily_trading(date: TradingDate = "", stock_no: str = "", name: str = "",
                                limit: Limit = DEFAULT_DISPLAY_LIMIT, offset: Offset = 0) -> str:
        """查詢上市股票單日成交資訊（收盤行情：開高低收、漲跌、成交量值與筆數、本益比）：預設最新交易日，
        也可指定過去日期；可查單一個股，或全市場收盤行情的快照用於篩選。
        單一股票一整個月的日K請用 get_stock_history。

        回傳：每支股票的代號、名稱、成交股數、成交金額、開高低收、漲跌、本益比

        Args:
            date: 查詢日期，格式 西元 YYYYMMDD，例如 "20260610"（選填，留空＝最新交易日）
            stock_no: 股票代號（選填），指定則只回傳該股票
            name: 股票名稱關鍵字（選填）
            limit: 回傳筆數上限（預設 50）
            offset: 跳過前 N 筆（預設 0，搭配 limit 分頁）
        """
        table = stock_quotes(_client, "ALLBUT0999", date)
        if table is None:
            return f"查無 {date or '最新交易日'} 的收盤行情資料，請確認該日期為交易日（非假日或週末）"
        date = table.date

        data = table.quotes
        if stock_no:
            data = [q for q in data if q.code == stock_no]
            if not data:
                return f"查無股票代號 {stock_no} 在 {date} 的收盤行情"
        if name:
            data = [q for q in data if name in q.name]
            if not data:
                return f"查無名稱包含「{name}」的股票在 {date} 的收盤行情"

        paged = Page(limit, offset).take(data)
        if paged.past_end:
            return paged.out_of_range(f"{date} 的收盤行情資料")

        header = f"【{date} 全市場每日收盤行情】（共 {paged.total} 筆"
        if paged.span():
            header += f"，{paged.span()}"
        header += "）\n"

        lines = [header]
        for q in paged.rows:
            change = printed(q.change_points)
            if q.direction in ("+", "-"):
                change = q.direction + change  # 漲跌價差 is unsigned; flat and 除權息 (X) print bare
            lines.append(
                f"{q.code} {q.name} | 開:{printed(q.open)} 高:{printed(q.high)} 低:{printed(q.low)} "
                f"收:{printed(q.close)} 漲跌:{change} | "
                f"量:{printed(q.volume)} 金額:{printed(q.value)} 筆數:{printed(q.transactions)} | 本益比:{printed(q.pe, '')}"
            )

        if paged.more():
            lines.append("\n" + paged.more())

        return "\n".join(lines)
