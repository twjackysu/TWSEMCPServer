"""TPEx (上櫃) valuation ratios and foreign shareholding, latest day or any past date.

Sources: www.tpex.org.tw website JSON afterTrading/peQryDate and insti/qfii.

peQryDate replaces the openapi tpex_mainboard_peratio_analysis tool: on 2026-09-29 both had
the same 889 stocks and, row by row, identical P/E, dividend per share, yield and P/B; the
website endpoint also has 股利年度 and 財報年/季 and accepts past dates. insti/qfii has no
openapi counterpart among our tools; it mirrors get_foreign_holdings for listed stocks.
"""

from typing import Optional
from fastmcp import FastMCP
from utils import TWSEAPIClient, handle_api_errors, format_list_response, DEFAULT_DISPLAY_LIMIT
from .history import TPEX_WWW, date_params, first_table, resp_date

PE_QRY_DATE_URL = f"{TPEX_WWW}/afterTrading/peQryDate"
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
    def get_otc_valuation(date: str = "", stock_no: str = "", name: str = "",
                          limit: int = DEFAULT_DISPLAY_LIMIT, offset: int = 0) -> str:
        """查詢上櫃股票本益比、殖利率、股價淨值比：預設最新交易日，也可指定過去日期。
        與上市的 get_stock_valuation_ratios 對應。

        Args:
            date: 查詢日期 YYYYMMDD（選填，留空＝最新交易日）
            stock_no: 股票代號（選填）
            name: 公司名稱關鍵字（選填）
            limit: 回傳筆數上限（預設 50）
            offset: 跳過前 N 筆（預設 0，搭配 limit 分頁）

        Returns:
            每支上櫃股的本益比、每股股利（股利年度）、殖利率(%)、股價淨值比（財報年/季）
        """
        params = date_params(date)
        if params is None:
            return "日期格式錯誤，請使用 YYYYMMDD，例如 \"20260929\""
        resp = _client.fetch_json(PE_QRY_DATE_URL, params={**params, "response": "json"})
        rows = first_table(resp).get("data") or []
        if not rows:
            return f"查無 {date or '最新交易日'} 的上櫃估值資料，請確認該日期為交易日（非假日或週末）"
        rows = _filter(rows, stock_no, name, 0, 1)

        def fmt(r):
            # r: 股票代號,公司名稱,本益比,每股股利,股利年度,殖利率(%),股價淨值比,財報年/季
            return (
                f"{r[0]} {r[1].strip()} | 本益比: {r[2]} | 殖利率: {r[5]}%（每股股利 {r[3]}，股利年度 {r[4]}）| "
                f"股價淨值比: {r[6]}（財報 {r[7]}）\n"
            )

        return format_list_response(rows, f" {resp_date(resp, date)} 上櫃股票本益比、殖利率及股價淨值比", fmt, limit, offset)

    @mcp.tool
    @handle_api_errors()
    def get_otc_foreign_holdings(date: str = "", stock_no: str = "", name: str = "",
                                 limit: int = DEFAULT_DISPLAY_LIMIT, offset: int = 0) -> str:
        """查詢上櫃股票僑外資及陸資持股比例：預設最新交易日，也可指定過去日期，依持股比率由高到低排行。
        與上市的 get_foreign_holdings 對應，適合追蹤外資在上櫃股的持股變化。

        Args:
            date: 查詢日期 YYYYMMDD（選填，留空＝最新交易日）
            stock_no: 股票代號（選填）
            name: 名稱關鍵字（選填）
            limit: 回傳筆數上限（預設 50；limit=20 即外資持股前 20 名）
            offset: 跳過前 N 筆（預設 0，搭配 limit 分頁）

        Returns:
            排行、代號、名稱、外資持股比率、尚可投資比率、法令投資上限、持有股數、發行股數
        """
        params = date_params(date)
        if params is None:
            return "日期格式錯誤，請使用 YYYYMMDD，例如 \"20260929\""
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
