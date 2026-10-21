"""TPEx (上櫃) tools from www.tpex.org.tw's website JSON endpoints.

The tpex.org.tw/openapi equivalents only return the latest trading day and fewer columns.
The website's own endpoints (``/www/zh-tw/...?response=json``) return the latest day when
``date`` is omitted and accept any past date otherwise, giving OTC stocks the same history
coverage TWSE stocks get from tools/history/.
"""

import re
from typing import Optional
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from utils import TWSEAPIClient, format_list_response, DEFAULT_DISPLAY_LIMIT
from toolkit import Limit, Offset, RequiredTradingDate, TradingDate, handle_api_errors
from utils.institutional import SIDES, SORT_LABELS, Investor, Side, rank
from sources.tpex.insti_daily import tpex_flows

TPEX_WWW = "https://www.tpex.org.tw/www/zh-tw"
TRADING_STOCK_URL = f"{TPEX_WWW}/afterTrading/tradingStock"
# insti/dailyTrade sect: EW 不含權證、牛熊證；EE 上櫃 ETF；AL 所有證券；或兩碼產業代碼
OTC_SECTS = {"": "EW", "stock": "EW", "etf": "EE", "all": "AL"}  # stock = EW minus 00-prefixed ETFs
MARGIN_BALANCE_URL = f"{TPEX_WWW}/margin/balance"


def date_params(date: str) -> dict:
    """``{"date": "YYYY/MM/DD"}`` for a YYYYMMDD date, ``{}`` for "" (latest day)."""
    return {"date": to_tpex_date(date)} if date else {}


def resp_date(resp, fallback: str) -> str:
    """The trading date TPEx actually answered for (YYYYMMDD), for the output header."""
    return str(resp.get("date") or fallback or "最新交易日") if isinstance(resp, dict) else fallback


def to_tpex_date(date: str) -> str:
    """"YYYYMMDD" → "YYYY/MM/DD", the format TPEx's website endpoints take."""
    return f"{date[:4]}/{date[4:6]}/{date[6:]}"


def first_table(resp) -> dict:
    """TPEx wraps each result in ``tables``; the per-stock table is always the first."""
    tables = resp.get("tables") if isinstance(resp, dict) else None
    return tables[0] if tables and isinstance(tables[0], dict) else {}


def filter_rows(rows: list, stock_no: str, name: str) -> list:
    """Keep rows whose 代號 (col 0) equals stock_no and whose 名稱 (col 1) contains name."""
    if stock_no:
        rows = [r for r in rows if r[0].strip() == stock_no.strip()]
    if name:
        rows = [r for r in rows if name in r[1]]
    return rows


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    """Register TPEx website tools."""
    _client = client or TWSEAPIClient.get_instance()

    @mcp.tool
    @handle_api_errors(use_code_param=True)
    def get_otc_stock_history(code: str, date: RequiredTradingDate) -> str:
        """查詢上櫃個股「指定月份」的每日成交資訊（日K：開高低收、成交量值）。
        與 get_otc_daily（OpenAPI，僅最新一日）不同，可回溯任意過去月份。
        上市股票請改用 get_stock_history。

        回傳：當月每個交易日的日期、成交張數、成交仟元、開盤、最高、最低、收盤、漲跌、筆數

        Args:
            code: 上櫃股票代號，例如 "6488"
            date: 該月任一天，格式 YYYYMMDD，例如 "20260801"（會回傳 2026 年 8 月整月）
        """
        tpex_date = to_tpex_date(date)
        resp = _client.fetch_json(
            TRADING_STOCK_URL, params={"code": code.strip(), "date": tpex_date, "response": "json"}
        )
        table = first_table(resp)
        rows = table.get("data") or []
        if not rows:
            return f"查無上櫃股票 {code} 在 {date[:6]} 的成交資料（請確認為上櫃股票代號，上市股票請用 get_stock_history）"

        name = resp.get("name", "")
        lines = [f"【{code} {name} 上櫃個股日成交資訊 {date[:4]}-{date[4:6]}】（共 {len(rows)} 個交易日）"]
        for r in rows:
            # r: 日期(民國),成交張數,成交仟元,開盤,最高,最低,收盤,漲跌,筆數
            lines.append(
                f"{r[0]} | 開:{r[3]} 高:{r[4]} 低:{r[5]} 收:{r[6]} 漲跌:{r[7]} | "
                f"量:{r[1]}張 值:{r[2]}仟元 筆數:{r[8]}"
            )
        return "\n".join(lines)

    @mcp.tool
    @handle_api_errors()
    def get_otc_institutional(date: TradingDate = "", stock_no: str = "", name: str = "", category: str = "",
                              sort_by: Investor = "total", side: Side = "abs",
                              limit: Limit = DEFAULT_DISPLAY_LIMIT, offset: Offset = 0) -> str:
        """查詢上櫃個股三大法人買賣超（單位：股）：可查單一股票，或做排行（例如上櫃外資買超前 20 名）。
        預設最新交易日，可查任意過去交易日；預設排除權證與牛熊證。
        上市股票請改用 get_twse_institutional_investors_summary（排行）或
        get_twse_institutional_investors_by_stock（單一個股）；上櫃市場整體的法人買賣金額請用
        get_otc_institutional_summary。

        回傳：每支股票的外資（不含外資自營商、外資自營商）、投信、自營商（自行買賣／避險）
        買賣超股數與三大法人合計

        Args:
            date: 查詢日期 YYYYMMDD（選填，留空＝最新交易日）
            stock_no: 股票代號（選填，指定時只回傳該股）
            name: 股票名稱關鍵字（選填）
            category: 範圍（選填）：留空＝不含權證、牛熊證（含 ETF，債券 ETF 常佔外資買賣超前幾名）；
                "stock"＝再排除 ETF；"etf"＝只看上櫃 ETF；"all"＝含權證；或產業代碼，例如 "24"（半導體業）
            sort_by: 依誰的買賣超排序：total（三大法人合計，預設）、foreign（外資，含外資自營商）、
                trust（投信）、dealer（自營商）
            side: buy（只列買超，由大到小）、sell（只列賣超，由大到小）、abs（依絕對值混排，預設）
            limit: 回傳筆數上限（預設 50）
            offset: 跳過前 N 筆（預設 0，搭配 limit 分頁）
        """
        sect = OTC_SECTS.get(category.strip().lower())
        if sect is None:
            sect = category.strip().upper() if re.fullmatch(r"[0-9A-Za-z]{2}", category.strip()) else None
        if sect is None:
            raise ToolError("category 必須留空，或是 stock、etf、all、產業代碼（例如 24）")
        report = tpex_flows(_client, sect, date)
        if report is None:
            return f"查無 {date or '最新交易日'} 的上櫃三大法人資料，請確認該日期為交易日（非假日或週末）及 category"
        day = report.date or date or "最新交易日"
        flows = report.flows
        if stock_no:
            flows = [f for f in flows if f.code == stock_no.strip()]
        if name:
            flows = [f for f in flows if name in f.name]
        if category.strip().lower() == "stock":
            flows = [f for f in flows if not f.code.startswith("00")]
        if not stock_no:
            flows = rank(flows, lambda f: f.net(sort_by), side)

        def fmt(f):
            return (
                f"{f.code} {f.name} | 外資:{f.foreign.net:,}（不含自營商 {f.foreign_ex_dealer.net:,}，"
                f"外資自營商 {f.foreign_dealer.net:,}）| 投信:{f.trust.net:,} | 自營商:{f.dealer.net:,}"
                f"（自行 {f.dealer_self.net:,}，避險 {f.dealer_hedge.net:,}）| 三大法人合計:{f.total_net:,}\n"
            )

        order = "" if stock_no else f"，依{SORT_LABELS[sort_by]}{SIDES[side]}排序"
        return format_list_response(flows, f" {day} 上櫃三大法人買賣超（單位：股{order}）", fmt, limit, offset)

    @mcp.tool
    @handle_api_errors()
    def get_otc_margin_balance(date: TradingDate = "", stock_no: str = "", name: str = "",
                               limit: Limit = DEFAULT_DISPLAY_LIMIT, offset: Offset = 0) -> str:
        """查詢上櫃股票融資融券餘額：預設最新交易日，也可回溯任意過去交易日。
        上市股票請改用 get_margin_balance。

        回傳：每支股票的融資（前日餘額/買進/賣出/現償/餘額/使用率/限額）、
        融券（前日餘額/賣出/買進/券償/餘額/使用率）、資券相抵；另附全市場合計

        Args:
            date: 查詢日期，格式 YYYYMMDD，例如 "20260803"（選填，留空＝最新交易日）
            stock_no: 股票代號（選填）
            name: 股票名稱關鍵字（選填）
            limit: 回傳筆數上限（預設 50）
            offset: 跳過前 N 筆（預設 0，搭配 limit 分頁）
        """
        params = date_params(date)
        resp = _client.fetch_json(MARGIN_BALANCE_URL, params={**params, "response": "json"})
        table = first_table(resp)
        rows = table.get("data") or []
        if not rows:
            return f"查無 {date or '最新交易日'} 的上櫃融資融券資料，請確認該日期為交易日（非假日或週末）"
        day = resp_date(resp, date)
        rows = filter_rows(rows, stock_no, name)

        def fmt(r):
            # r: 代號,名稱,前資餘額,資買,資賣,現償,資餘額,資屬證金,資使用率,資限額,
            #    前券餘額,券賣,券買,券償,券餘額,券屬證金,券使用率,券限額,資券相抵,備註
            return (
                f"{r[0]} {r[1]} | 融資: 前日{r[2]} 買{r[3]} 賣{r[4]} 現償{r[5]} 餘額{r[6]} 使用率{r[8]}% 限額{r[9]} | "
                f"融券: 前日{r[10]} 賣{r[11]} 買{r[12]} 券償{r[13]} 餘額{r[14]} 使用率{r[16]}% | 資券相抵{r[18]}"
                + (f" | 備註:{r[19]}" if len(r) > 19 and r[19].strip() else "")
                + "\n"
            )

        body = format_list_response(rows, f" {day} 上櫃融資融券餘額（單位：張）", fmt, limit, offset)
        # summary 列（合計張數、融資金額）不在 data 裡，只在未篩選個股時附上
        summary = table.get("summary") or []
        if summary and not stock_no and not name:
            body += "\n\n全市場合計: " + " / ".join(
                f"{s[1]} 資餘額{s[6]} 券餘額{s[14]}" if s[14] else f"{s[1]} 資餘額{s[6]}"
                for s in summary if len(s) > 14
            )
        return body
