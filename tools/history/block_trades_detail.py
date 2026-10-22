"""TWSE block trade (鉅額交易) daily detail, per-transaction, from BFIAUU (sources/twse/bfiauu.py)."""

from typing import Optional
from fastmcp import FastMCP
from utils import (
    TWSEAPIClient,
    DEFAULT_DISPLAY_LIMIT,
    Page,
    printed,
)
from toolkit import Limit, Offset, RequiredTradingDate, handle_api_errors
from sources.twse.bfiauu import block_trades


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    """Register TWSE block trade detail tools."""
    _client = client or TWSEAPIClient.get_instance()

    @mcp.tool
    @handle_api_errors()
    def get_block_trades_detail(date: RequiredTradingDate, stock_no: str = "", name: str = "",
                                 limit: Limit = DEFAULT_DISPLAY_LIMIT, offset: Offset = 0) -> str:
        """查詢集中市場鉅額交易逐筆明細（含配對交易、盤後鉅額等交易別）。
        與 get_block_trades_daily（openapi 版，僅有量值統計總數）不同，此工具回傳每一筆
        鉅額交易的個股代號、交易別、成交價與成交量金額。
        注意：來源端點不支援伺服器端股票代號篩選，stock_no/name 為本地端過濾。

        回傳：每筆鉅額交易的股票代號、名稱、交易別、成交價、成交股數、成交金額

        Args:
            date: 查詢日期，格式 西元 YYYYMMDD，例如 "20260610"（需為交易日）
            stock_no: 股票代號（選填），指定則只回傳該股票的鉅額交易
            name: 股票名稱關鍵字（選填）
            limit: 回傳筆數上限（預設 50）
            offset: 跳過前 N 筆（預設 0，搭配 limit 分頁）
        """
        day = block_trades(_client, date)
        if day is None:
            return f"查無 {date} 的鉅額交易資料，請確認該日期為交易日（非假日或週末）"

        # The gateway leaves out the closing 總計 row (the day's totals): kept, it counted as one more
        # trade, far larger than any real one.
        trades = day.trades
        if not trades:
            return f"查無 {date} 的鉅額交易資料"

        if stock_no:
            trades = [t for t in trades if t.code == stock_no]
            if not trades:
                return f"查無股票代號 {stock_no} 在 {date} 的鉅額交易資料"
        if name:
            trades = [t for t in trades if name in t.name]
            if not trades:
                return f"查無名稱包含「{name}」的股票在 {date} 的鉅額交易資料"

        paged = Page(limit, offset).take(trades)
        if paged.past_end:
            return paged.out_of_range(f"{date} 的鉅額交易資料")

        title = day.title or f"{date} 鉅額交易日成交資訊"
        header = f"【{title}】（共 {paged.total} 筆"
        if paged.span():
            header += f"，{paged.span()}"
        header += "）\n"

        lines = [header]
        for t in paged.rows:
            kind = f"{t.kind} {t.settlement}" if t.settlement else t.kind  # 交割期別 until 2011-12-16
            lines.append(f"{t.code} {t.name} | {kind} | 價:{printed(t.price)} 量:{printed(t.volume)} 金額:{printed(t.value)}")

        if paged.more():
            lines.append("\n" + paged.more())

        return "\n".join(lines)
