"""TPEx (上櫃) tools from www.tpex.org.tw's website JSON endpoints.

The tpex.org.tw/openapi equivalents only return the latest trading day and fewer columns.
The website's own endpoints (``/www/zh-tw/...?response=json``) return the latest day when
``date`` is omitted and accept any past date otherwise, giving OTC stocks the same history
coverage TWSE stocks get from tools/history/.
"""

from datetime import datetime
from typing import Optional
from fastmcp import FastMCP
from utils import TWSEAPIClient, handle_api_errors, format_list_response, DEFAULT_DISPLAY_LIMIT

TPEX_WWW = "https://www.tpex.org.tw/www/zh-tw"
TRADING_STOCK_URL = f"{TPEX_WWW}/afterTrading/tradingStock"
INSTI_DAILY_URL = f"{TPEX_WWW}/insti/dailyTrade"
MARGIN_BALANCE_URL = f"{TPEX_WWW}/margin/balance"


def date_params(date: str) -> Optional[dict]:
    """``{"date": "YYYY/MM/DD"}`` for a YYYYMMDD date, ``{}`` for "" (latest day), None if invalid."""
    if not date.strip():
        return {}
    tpex_date = to_tpex_date(date)
    return {"date": tpex_date} if tpex_date else None


def resp_date(resp, fallback: str) -> str:
    """The trading date TPEx actually answered for (YYYYMMDD), for the output header."""
    return str(resp.get("date") or fallback or "最新交易日") if isinstance(resp, dict) else fallback


def to_tpex_date(date: str) -> Optional[str]:
    """"YYYYMMDD" → "YYYY/MM/DD" (the format TPEx's website endpoints take), or None."""
    try:
        return datetime.strptime(date.strip(), "%Y%m%d").strftime("%Y/%m/%d")
    except ValueError:
        return None


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
    def get_otc_stock_history(code: str, date: str) -> str:
        """查詢上櫃個股「指定月份」的每日成交資訊（日K：開高低收、成交量值）。
        與 get_otc_daily（OpenAPI，僅最新一日）不同，可回溯任意過去月份。
        上市股票請改用 get_stock_history。

        Args:
            code: 上櫃股票代號，例如 "6488"
            date: 該月任一天，格式 YYYYMMDD，例如 "20260801"（會回傳 2026 年 8 月整月）

        Returns:
            當月每個交易日的日期、成交張數、成交仟元、開盤、最高、最低、收盤、漲跌、筆數
        """
        tpex_date = to_tpex_date(date)
        if not tpex_date:
            return "日期格式錯誤，請使用 YYYYMMDD，例如 \"20260801\""
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
    def get_otc_institutional(date: str = "", stock_no: str = "", name: str = "",
                              limit: int = DEFAULT_DISPLAY_LIMIT, offset: int = 0) -> str:
        """查詢上櫃股票三大法人買賣超明細：預設最新交易日，也可回溯任意過去交易日。
        上市股票請改用 get_twse_institutional_investors_by_stock；上櫃市場彙總請用
        get_otc_institutional_summary。

        Args:
            date: 查詢日期，格式 YYYYMMDD，例如 "20260803"（選填，留空＝最新交易日）
            stock_no: 股票代號（選填）
            name: 股票名稱關鍵字（選填）
            limit: 回傳筆數上限（預設 50）
            offset: 跳過前 N 筆（預設 0，搭配 limit 分頁）

        Returns:
            每支股票的外資（不含外資自營商）、外資自營商、投信、自營商（自行買賣／避險）
            買賣超股數與三大法人合計
        """
        params = date_params(date)
        if params is None:
            return "日期格式錯誤，請使用 YYYYMMDD，例如 \"20260803\""
        resp = _client.fetch_json(
            INSTI_DAILY_URL, params={"type": "Daily", "sect": "EW", **params, "response": "json"}
        )
        rows = first_table(resp).get("data") or []
        if not rows:
            return f"查無 {date or '最新交易日'} 的上櫃三大法人資料，請確認該日期為交易日（非假日或週末）"
        day = resp_date(resp, date)
        rows = filter_rows(rows, stock_no, name)

        def fmt(r):
            # r: 代號,名稱, 外資及陸資(不含外資自營商) 買/賣/超 [2:5], 外資自營商 [5:8],
            #    外資及陸資合計 [8:11], 投信 [11:14], 自營商(自行買賣) [14:17],
            #    自營商(避險) [17:20], 自營商合計 [20:23], 三大法人買賣超合計 [23]
            return (
                f"{r[0]} {r[1]} | 外資:{r[10]}（不含自營商 {r[4]}，外資自營商 {r[7]}）| "
                f"投信:{r[13]} | 自營商:{r[22]}（自行 {r[16]}，避險 {r[19]}）| 三大法人合計:{r[23]}\n"
            )

        return format_list_response(rows, f" {day} 上櫃三大法人買賣超（單位：股）", fmt, limit, offset)

    @mcp.tool
    @handle_api_errors()
    def get_otc_margin_balance(date: str = "", stock_no: str = "", name: str = "",
                               limit: int = DEFAULT_DISPLAY_LIMIT, offset: int = 0) -> str:
        """查詢上櫃股票融資融券餘額：預設最新交易日，也可回溯任意過去交易日。
        上市股票請改用 get_margin_balance。

        Args:
            date: 查詢日期，格式 YYYYMMDD，例如 "20260803"（選填，留空＝最新交易日）
            stock_no: 股票代號（選填）
            name: 股票名稱關鍵字（選填）
            limit: 回傳筆數上限（預設 50）
            offset: 跳過前 N 筆（預設 0，搭配 limit 分頁）

        Returns:
            每支股票的融資（前日餘額/買進/賣出/現償/餘額/使用率/限額）、
            融券（前日餘額/賣出/買進/券償/餘額/使用率）、資券相抵；另附全市場合計
        """
        params = date_params(date)
        if params is None:
            return "日期格式錯誤，請使用 YYYYMMDD，例如 \"20260803\""
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
