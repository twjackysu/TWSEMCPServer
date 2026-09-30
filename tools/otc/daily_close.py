"""TPEx (上櫃) whole-market daily quotes: latest day from openapi, past dates from the website.

The two sources are not interchangeable, so both are kept behind one tool. On 2026-09-29
they listed the same 11,730 securities, but openapi tpex_mainboard_daily_close_quotes
counts 定價 (fixed-price) trades in volume/amount/count (3,007 cells differed, openapi always
larger) and has 均價 and 次日參考價, while the website's afterTrading/otc excludes 定價 trades
("不含定價") and has neither column — but it is the only one that accepts a past date.
"""

from typing import Optional
from fastmcp import FastMCP
from utils import TWSEAPIClient, handle_api_errors, DEFAULT_DISPLAY_LIMIT, MSG_OFFSET_OUT_OF_RANGE, format_list_response
from .history import TPEX_WWW, date_params, filter_rows, first_table, resp_date

TPEX_DAILY_CLOSE_URL = "https://www.tpex.org.tw/openapi/v1/tpex_mainboard_daily_close_quotes"
OTC_QUOTES_URL = f"{TPEX_WWW}/afterTrading/otc"
# type=EW is stocks and ETFs (~1,000 rows); type=AL adds ~10,700 warrants (~1.5 MB), which
# TPEx cut off mid-transfer on 1 of 5 test downloads. EW first, AL only when a requested
# code isn't in it (i.e. a warrant).
TYPE_STOCKS, TYPE_ALL = "EW", "AL"
# A past trading day's quotes never change.
PAST_QUOTES_CACHE_TTL = 600


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    """Register OTC daily close tools."""
    _client = client or TWSEAPIClient.get_instance()

    def _latest(stock_no: str, name: str, limit: int, offset: int) -> str:
        data = _client.fetch_json(TPEX_DAILY_CLOSE_URL)
        if not isinstance(data, list) or not data:
            return "查無上櫃市場收盤行情資料"

        if stock_no:
            data = [d for d in data if d.get("SecuritiesCompanyCode", "").strip() == stock_no.strip()]
            if not data:
                return f"查無上櫃股票代號 {stock_no} 的收盤行情"
        if name:
            data = [d for d in data if name in d.get("CompanyName", "")]
            if not data:
                return f"查無名稱包含「{name}」的上櫃股票收盤行情"

        total = len(data)
        page_data = data[offset:offset + limit]
        if not page_data:
            return MSG_OFFSET_OUT_OF_RANGE.format(
                offset=offset, data_type="上櫃市場收盤行情資料", count=total
            )
        end = min(offset + limit, total)

        header = f"【上櫃市場收盤行情 {page_data[0].get('Date', '')}】（共 {total} 筆"
        if total > limit or offset > 0:
            header += f"，顯示第 {offset + 1}–{end} 筆"
        header += "）\n"

        lines = [header]
        for item in page_data:
            lines.append(
                f"{item.get('SecuritiesCompanyCode', '?')} {item.get('CompanyName', '?')} | "
                f"收: {item.get('Close', '-')} | 漲跌: {str(item.get('Change', '-')).strip()} | "
                f"開: {item.get('Open', '-')} | 高: {item.get('High', '-')} | 低: {item.get('Low', '-')} | "
                f"均價: {item.get('Average', '-')} | 量: {item.get('TradingShares', '-')} | "
                f"金額: {item.get('TransactionAmount', '-')} | 筆數: {item.get('TransactionNumber', '-')}"
            )

        remaining = total - offset - limit
        if remaining > 0:
            lines.append(f"\n...還有 {remaining} 筆，使用 offset={offset + limit} 查看更多")
        return "\n".join(lines)

    @mcp.tool
    @handle_api_errors()
    def get_otc_daily(date: str = "", stock_no: str = "", name: str = "",
                      limit: int = DEFAULT_DISPLAY_LIMIT, offset: int = 0) -> str:
        """查詢上櫃（OTC）市場的單日收盤行情：預設最新交易日（含權證等全部證券），也可指定過去日期
        （清單為股票及 ETF；指定權證代號時會自動查詢全部證券）。
        可查單一個股或整個市場的快照。單一上櫃股票整月日K請用 get_otc_stock_history。
        注意：指定 date 時資料來自櫃買中心網站，成交量值「不含定價交易」且沒有均價欄；
        不帶 date（最新交易日）時含定價交易並附均價。

        Args:
            date: 查詢日期 YYYYMMDD（選填，留空＝最新交易日）
            stock_no: 股票代號（選填）
            name: 名稱關鍵字（選填）
            limit: 回傳筆數上限（預設 50）
            offset: 跳過前 N 筆（預設 0，搭配 limit 分頁）

        Returns:
            每支上櫃證券的收盤、漲跌、開高低、成交股數、成交金額、成交筆數（最新交易日另含均價）
        """
        if not date.strip():
            return _latest(stock_no, name, limit, offset)

        params = date_params(date)
        if params is None:
            return "日期格式錯誤，請使用 YYYYMMDD，例如 \"20260929\""
        def fetch(security_type):
            resp = _client.fetch_json(
                OTC_QUOTES_URL, params={**params, "type": security_type, "response": "json"},
                cache_ttl=PAST_QUOTES_CACHE_TTL,
            )
            return resp, first_table(resp).get("data") or []

        resp, rows = fetch(TYPE_STOCKS)
        if not rows:
            return f"查無 {date} 的上櫃收盤行情，請確認該日期為交易日（非假日或週末）"
        scope = "股票及 ETF"
        if stock_no and not filter_rows(rows, stock_no, ""):
            resp, rows = fetch(TYPE_ALL)
            scope = "含權證等全部證券"
        rows = filter_rows(rows, stock_no, name)

        def fmt(r):
            # r: 代號,名稱,收盤,漲跌,開盤,最高,最低,成交股數,成交金額(元),成交筆數,最後買價,最後買量,
            #    最後賣價,最後賣量,發行股數,次日漲停價,次日跌停價
            return (
                f"{r[0]} {r[1]} | 收: {r[2]} | 漲跌: {r[3]} | 開: {r[4]} | 高: {r[5]} | 低: {r[6]} | "
                f"量: {r[7]} | 金額: {r[8]} | 筆數: {r[9]} | 最後買/賣: {r[10]}/{r[12]}\n"
            )

        return format_list_response(
            rows, f" {resp_date(resp, date)} 上櫃{scope}收盤行情（成交量值不含定價交易）", fmt, limit, offset
        )
