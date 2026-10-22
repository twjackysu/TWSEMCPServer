"""TPEx (上櫃) tools from www.tpex.org.tw's website JSON endpoints.

The tpex.org.tw/openapi equivalents only return the latest trading day and fewer columns.
The website's own endpoints (``/www/zh-tw/...?response=json``) return the latest day when
``date`` is omitted and accept any past date otherwise, giving OTC stocks the same history
coverage TWSE stocks get from tools/history/. Each is read through its gateway in sources/tpex/.
"""

import re
from typing import Optional
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from utils import TWSEAPIClient, format_list_response, printed, DEFAULT_DISPLAY_LIMIT
from toolkit import Limit, Offset, RequiredTradingDate, TradingDate, handle_api_errors
from utils.date_helper import roc_date
from utils.institutional import SIDES, SORT_LABELS, Investor, Side, rank
from sources.tpex.insti_daily import tpex_flows
from sources.tpex.margin_balance import otc_margin_balances
from sources.tpex.trading_stock import trading_stock_month

# insti/dailyTrade sect: EW 不含權證、牛熊證；EE 上櫃 ETF；AL 所有證券；或兩碼產業代碼
OTC_SECTS = {"": "EW", "stock": "EW", "etf": "EE", "all": "AL"}  # stock = EW minus 00-prefixed ETFs


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    """Register TPEx website tools."""
    _client = client or TWSEAPIClient.get_instance()

    @mcp.tool
    @handle_api_errors(use_code_param=True)
    def get_otc_stock_history(code: str, date: RequiredTradingDate) -> str:
        """查詢上櫃個股「指定月份」的每日成交資訊（日K／K線、歷史股價：開高低收、成交量值）。
        與 get_otc_daily（OpenAPI，僅最新一日）不同，可回溯任意過去月份。
        上市股票請改用 get_stock_history。

        回傳：當月每個交易日的日期、成交張數、成交仟元、開盤、最高、最低、收盤、漲跌、筆數

        Args:
            code: 上櫃股票代號，例如 "6488"
            date: 該月任一天，格式 西元 YYYYMMDD，例如 "20260801"（會回傳 2026 年 8 月整月）
        """
        month = trading_stock_month(_client, code.strip(), int(date[:4]), int(date[4:6]))
        if month is None:
            return f"查無上櫃股票 {code} 在 {date[:6]} 的成交資料（請確認為上櫃股票代號，上市股票請用 get_stock_history）"

        lines = [f"【{code} {month.name} 上櫃個股日成交資訊 {date[:4]}-{date[4:6]}】（共 {len(month.rows)} 個交易日）"]
        for r in month.rows:
            lines.append(
                f"{roc_date(f'{r.day:%Y%m%d}')} | 開:{printed(r.open)} 高:{printed(r.high)} 低:{printed(r.low)} "
                f"收:{printed(r.close)} 漲跌:{r.change} | "
                f"量:{printed(r.lots)}張 值:{printed(r.value_thousands)}仟元 筆數:{printed(r.transactions)}"
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
            date: 查詢日期 西元 YYYYMMDD（選填，留空＝最新交易日）
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
            date: 查詢日期，格式 西元 YYYYMMDD，例如 "20260803"（選填，留空＝最新交易日）
            stock_no: 股票代號（選填）
            name: 股票名稱關鍵字（選填）
            limit: 回傳筆數上限（預設 50）
            offset: 跳過前 N 筆（預設 0，搭配 limit 分頁）
        """
        report = otc_margin_balances(_client, date)
        if not report.balances:
            return f"查無 {date or '最新交易日'} 的上櫃融資融券資料，請確認該日期為交易日（非假日或週末）"
        day = report.date or date or "最新交易日"
        rows = [b for b in report.balances
                if (not stock_no or b.code == stock_no.strip()) and (not name or name in b.name)]

        def fmt(b):
            m, s = b.margin, b.short
            return (
                f"{b.code} {b.name} | 融資: 前日{printed(m.previous)} 買{printed(m.buy)} 賣{printed(m.sell)} "
                f"現償{printed(m.repaid)} 餘額{printed(m.balance)} 使用率{printed(m.usage)}% 限額{printed(m.limit)} | "
                f"融券: 前日{printed(s.previous)} 賣{printed(s.sell)} 買{printed(s.buy)} 券償{printed(s.repaid)} "
                f"餘額{printed(s.balance)} 使用率{printed(s.usage)}% | 資券相抵{printed(b.offset)}"
                + (f" | 備註:{b.note}" if b.note else "")
                + "\n"
            )

        body = format_list_response(rows, f" {day} 上櫃融資融券餘額（單位：張）", fmt, limit, offset)
        # 合計張數、融資金額（summary）只在未篩選個股時附上；融資金那列沒有券餘額
        if report.totals and not stock_no and not name:
            body += "\n\n全市場合計: " + " / ".join(
                f"{t.label} 資餘額{printed(t.margin_balance)}"
                + (f" 券餘額{printed(t.short_balance)}" if t.short_balance is not None else "")
                for t in report.totals
            )
        return body
