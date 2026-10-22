"""Margin trading (融資融券) balances of listed stocks, latest or any past date.

Replaces the OpenAPI /exchangeReport/MI_MARGN tool (get_margin_trading_info): it only
served the latest day and on 2026-09-29 carried the same stocks and values as this
endpoint's per-stock table, without the market-wide 信用交易統計 table.
Read through the MI_MARGN gateway (``sources.twse.mi_margn``).
"""

from datetime import datetime, timedelta
from typing import Optional
from fastmcp import FastMCP
from sources.twse.mi_margn import DETAIL_FIELDS, margin_balances
from utils import TWSEAPIClient, DEFAULT_DISPLAY_LIMIT, Page, printed
from toolkit import Limit, Offset, TradingDate, handle_api_errors

MAX_RETRY_DAYS = 7


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    """Register margin balance tools."""
    _client = client or TWSEAPIClient.get_instance()

    @mcp.tool
    @handle_api_errors()
    def get_margin_balance(date: TradingDate = "", stock_no: str = "", name: str = "",
                           limit: Limit = DEFAULT_DISPLAY_LIMIT, offset: Offset = 0) -> str:
        """查詢上市股票融資融券餘額：預設最新交易日，也可指定過去日期，用於判斷槓桿水位與多空情緒。
        若指定日期非交易日，會自動往前尋找最近的交易日資料。
        未指定個股時附上全市場信用交易統計（融資、融券、融資金額）。上櫃股票請用 get_otc_margin_balance。

        回傳：每支股票的融資買進、賣出、餘額、融券賣出、買進、餘額、資券互抵等資料

        Args:
            date: 查詢日期 西元 YYYYMMDD（選填，留空＝最新交易日）
            stock_no: 股票代號（選填），若指定則只回傳該股票的融資融券資料
            name: 股票名稱關鍵字（選填）
            limit: 回傳筆數上限（預設 50）。全市場約 1300 檔，未分頁的完整輸出逾 100KB
            offset: 跳過前 N 筆（預設 0，搭配 limit 分頁）
        """
        if not date:
            # 不帶 date 時上游直接回最新交易日
            day = margin_balances(_client)
            if day is None:
                return "查無最新交易日的融資融券資料"
            actual_date = day.date or "最新交易日"
        else:
            current_date = datetime.strptime(date, "%Y%m%d")
            for _ in range(MAX_RETRY_DAYS):
                actual_date = current_date.strftime("%Y%m%d")
                day = margin_balances(_client, actual_date)
                if day is not None:
                    break
                current_date -= timedelta(days=1)
            else:
                return f"查無 {date} 前後的融資融券資料"

        data = day.balances
        if not data:
            return f"查無 {actual_date} 的融資融券資料"

        if stock_no:
            data = [b for b in data if b.code == stock_no.strip()]
            if not data:
                return f"查無股票代號 {stock_no} 在 {actual_date} 的融資融券資料"
        if name:
            data = [b for b in data if name in b.name]
            if not data:
                return f"查無名稱包含「{name}」的股票在 {actual_date} 的融資融券資料"

        paged = Page(limit, offset).take(data)
        if paged.past_end:
            return paged.out_of_range(f"{actual_date} 的融資融券資料")

        date_note = f"（原查詢 {date}，實際資料日 {actual_date}）" if date and actual_date != date else ""
        span = f"，{paged.span()}" if paged.span() else ""
        lines = [f"【融資融券餘額 - {actual_date}】{date_note}（共 {paged.total} 筆{span}）\n"]

        if day.totals and not stock_no and not name:
            lines.append("全市場信用交易統計（買進/賣出/償還/前日餘額/今日餘額）:")
            for t in day.totals:
                lines.append("  " + " | ".join([t.item] + [printed(v) for v in (t.buy, t.sell, t.repaid, t.previous, t.today)]))
            lines.append("")

        # 欄位名稱照證交所公布的寫法（融資、融券各有一組買進…次一營業日限額）
        lines.append("欄位: " + " | ".join(name.split("/")[-1] for name in DETAIL_FIELDS) + "\n")

        for b in paged.rows:
            figures = [b.margin.buy, b.margin.sell, b.margin.repaid, b.margin.previous, b.margin.today,
                       b.margin.next_day_limit, b.short.buy, b.short.sell, b.short.repaid, b.short.previous,
                       b.short.today, b.short.next_day_limit, b.offset]
            lines.append(" | ".join([b.code, b.name] + [printed(v) for v in figures] + [b.note]))

        if paged.more():
            lines.append("\n" + paged.more())

        return "\n".join(lines)
