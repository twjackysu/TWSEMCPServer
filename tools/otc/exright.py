"""OTC (上櫃) ex-rights / ex-dividend results (除權除息計算結果), today or any date range.

Source: www.tpex.org.tw website JSON bulletin/exDailyQ, read through sources/tpex/ex_daily_q.py.
It replaces the openapi tpex_exright_daily tool: on 2026-09-30 the openapi endpoint's only row
(8440) matched this endpoint's row for that day in all 18 value columns, and this endpoint also
lists the next day's pre-announced results and accepts any past range (e.g. 2024-01～2026-09 in
one call). The listed-market counterpart is get_exright_results_history (TWSE TWT49U).
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional
from fastmcp import FastMCP
from utils import TWSEAPIClient, format_list_response, DEFAULT_DISPLAY_LIMIT
from toolkit import Limit, Offset, TradingDate, handle_api_errors
from utils.date_helper import roc_date
from sources.tpex.ex_daily_q import otc_exright_results


def _text(value: Optional[Decimal]) -> str:
    """A number as TPEx prints it here: no thousands separators, its published decimals ("0.00000000")."""
    return "--" if value is None else f"{value:f}"


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    """Register OTC ex-rights/dividends tools."""
    _client = client or TWSEAPIClient.get_instance()

    @mcp.tool
    @handle_api_errors()
    def get_otc_exright(start_date: TradingDate = "", end_date: TradingDate = "", stock_no: str = "",
                        limit: Limit = DEFAULT_DISPLAY_LIMIT, offset: Offset = 0) -> str:
        """查詢上櫃股票除權除息計算結果：預設今天與下一個交易日，也可指定任意過去區間。
        可用於還原權息、計算填權息。上市股票請用 get_exright_results_history。

        回傳：除權息日期、代號、名稱、類型、除權息前收盤價、參考價、權值、息值、漲跌停價、
        開始交易基準價、現金股利、每仟股無償配股、現金增資股數與認購價

        Args:
            start_date: 起始日期 西元 YYYYMMDD（選填，留空＝今天起）
            end_date: 結束日期 西元 YYYYMMDD（選填，預設同 start_date）
            stock_no: 股票代號（選填）
            limit: 回傳筆數上限（預設 50）
            offset: 跳過前 N 筆（預設 0，搭配 limit 分頁）
        """
        start = end = None
        if start_date or end_date:
            start = datetime.strptime(start_date or end_date, "%Y%m%d").date()
            end = datetime.strptime(end_date or start_date, "%Y%m%d").date()
        report = otc_exright_results(_client, start, end)
        served = report.period.replace("~", "～")
        if not report.results:
            return f"查無 {served or '指定期間'} 的上櫃除權息資料"
        rows = [r for r in report.results if not stock_no or r.code == stock_no.strip()]

        def fmt(r):
            capital = f" | 現增:{r.cash_capital_shares}股@{_text(r.cash_capital_price)}" if r.cash_capital_shares else ""
            return (
                f"{roc_date(f'{r.day:%Y%m%d}')} | {r.code} {r.name} | {r.kind} | 前收:{_text(r.close_before)} "
                f"參考價:{_text(r.reference)}（權值 {_text(r.rights)} 息值 {_text(r.dividend)}）| "
                f"現金股利:{_text(r.cash_dividend)} 每仟股配股:{_text(r.stock_dividend)} | 漲停:{_text(r.limit_up)} "
                f"跌停:{_text(r.limit_down)} 開始交易基準價:{_text(r.opening_reference)}{capital}\n"
            )

        return format_list_response(rows, f" {served} 上櫃除權除息計算結果", fmt, limit, offset)
