"""TPEx (上櫃) valuation ratios and foreign shareholding, latest day or any past date.

Sources: www.tpex.org.tw website JSON afterTrading/peQryDate (through sources/tpex/pe_qry_date.py)
and insti/qfii.

peQryDate replaces the openapi tpex_mainboard_peratio_analysis tool: on 2026-09-29 both had
the same 889 stocks and, row by row, identical P/E, dividend per share, yield and P/B; the
website endpoint also has 股利年度 and 財報年/季 and accepts past dates. insti/qfii has no
openapi counterpart among our tools; it mirrors get_foreign_holdings for listed stocks.
"""

from typing import Optional
from fastmcp import FastMCP
from utils import TWSEAPIClient, format_list_response, DEFAULT_DISPLAY_LIMIT
from toolkit import Limit, Offset, TradingDate, handle_api_errors
from sources.tpex.pe_qry_date import otc_valuation_ratios
from .history import TPEX_WWW, date_params, first_table, resp_date

QFII_URL = f"{TPEX_WWW}/insti/qfii"


def _filter(rows: list, stock_no: str, name: str, code_col: int, name_col: int) -> list:
    if stock_no:
        rows = [r for r in rows if r[code_col].strip() == stock_no.strip()]
    if name:
        rows = [r for r in rows if name in r[name_col]]
    return rows


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    """Register TPEx valuation and foreign-holding tools."""
    _client = client or TWSEAPIClient.get_instance()

    @mcp.tool
    @handle_api_errors()
    def get_otc_valuation(date: TradingDate = "", stock_no: str = "", name: str = "",
                          limit: Limit = DEFAULT_DISPLAY_LIMIT, offset: Offset = 0) -> str:
        """查詢上櫃股票本益比、殖利率、股價淨值比：預設最新交易日，也可指定過去日期。
        與上市的 get_stock_valuation_ratios 對應。

        回傳：每支上櫃股的本益比、每股股利（股利年度）、殖利率(%)、股價淨值比（財報年/季）

        Args:
            date: 查詢日期 西元 YYYYMMDD（選填，留空＝最新交易日）
            stock_no: 股票代號（選填）
            name: 公司名稱關鍵字（選填）
            limit: 回傳筆數上限（預設 50）
            offset: 跳過前 N 筆（預設 0，搭配 limit 分頁）
        """
        report = otc_valuation_ratios(_client, date)
        if not report.valuations:
            return f"查無 {date or '最新交易日'} 的上櫃估值資料，請確認該日期為交易日（非假日或週末）"
        valuations = [v for v in report.valuations
                      if (not stock_no or v.code == stock_no.strip()) and (not name or name in v.name)]

        def text(value):
            return "N/A" if value is None else f"{value:f}"  # as TPEx prints it: no separators, all its decimals

        def fmt(v):
            fiscal = f"（財報 {v.fiscal}）" if v.fiscal else ""  # 財報年/季 is published from 2025-01-02
            return (
                f"{v.code} {v.name} | 本益比: {text(v.pe)} | 殖利率: {text(v.dividend_yield)}%（每股股利 "
                f"{text(v.dividend_per_share)}，股利年度 {v.dividend_year}）| 股價淨值比: {text(v.pb)}{fiscal}\n"
            )

        day = report.date or date or "最新交易日"
        return format_list_response(valuations, f" {day} 上櫃股票本益比、殖利率及股價淨值比", fmt, limit, offset)

    @mcp.tool
    @handle_api_errors()
    def get_otc_foreign_holdings(date: TradingDate = "", stock_no: str = "", name: str = "",
                                 limit: Limit = DEFAULT_DISPLAY_LIMIT, offset: Offset = 0) -> str:
        """查詢上櫃股票僑外資及陸資持股比例：預設最新交易日，也可指定過去日期，依持股比率由高到低排行。
        與上市的 get_foreign_holdings 對應，適合追蹤外資在上櫃股的持股變化。

        回傳：排行、代號、名稱、外資持股比率、尚可投資比率、法令投資上限、持有股數、發行股數

        Args:
            date: 查詢日期 西元 YYYYMMDD（選填，留空＝最新交易日）
            stock_no: 股票代號（選填）
            name: 名稱關鍵字（選填）
            limit: 回傳筆數上限（預設 50；limit=20 即外資持股前 20 名）
            offset: 跳過前 N 筆（預設 0，搭配 limit 分頁）
        """
        params = date_params(date)
        resp = _client.fetch_json(QFII_URL, params={**params, "response": "json"})
        rows = first_table(resp).get("data") or []
        if not rows:
            return f"查無 {date or '最新交易日'} 的上櫃外資持股資料，請確認該日期為交易日（非假日或週末）"
        rows = _filter(rows, stock_no, name, 1, 2)

        def fmt(r):
            # r: 排行,代號,名稱,發行股數(A),尚可投資股數,持有股數(C),尚可投資比率,持股比率,法令投資上限比率,備註
            note = f" | 備註:{r[9]}" if len(r) > 9 and r[9].strip() else ""
            return (
                f"#{r[0]} {r[1]} {r[2]} | 外資持股比率:{r[7]} | 尚可投資比率:{r[6]} | 投資上限:{r[8]} | "
                f"持有股數:{r[5]} | 發行股數:{r[3]}{note}\n"
            )

        return format_list_response(rows, f" {resp_date(resp, date)} 上櫃股票僑外資及陸資持股（依持股比率排行）", fmt, limit, offset)
