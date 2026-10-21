"""TWSE listed stocks institutional (三大法人) trading data, per stock (T86, shares).

``selectType``: ALL is every security — ~18,600 of the ~20,000 rows are warrants / CBBCs —
ALLBUT0999 excludes those (~1,300 rows), 0099P is ETFs only, and a two-digit industry code
(e.g. 24 半導體業) one industry. Without ``date`` T86 returns the latest trading day.
Rows come from the gateway (sources/twse/t86.py) as InstitutionalFlow, the record the OTC tool
(tools/otc/history.py) ranks too.
"""

import re
from typing import List, Optional
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from utils import TWSEAPIClient, DEFAULT_DISPLAY_LIMIT, Page
from toolkit import handle_api_errors
from utils.institutional import SIDES, SORT_LABELS, check_choice, rank
from sources.institutional import Trades
from sources.twse.t86 import t86_flows

# "stock" is ALLBUT0999 minus ETFs: on both markets every ETF code starts with 00 and every
# 00 code is an ETF (checked 2026-10-16 against T86 0099P and TPEx sect EE).
CATEGORIES = {"": "ALLBUT0999", "stock": "ALLBUT0999", "etf": "0099P", "all": "ALL"}


def _section(heading: str, trades: Trades) -> List[str]:
    return [heading, f"  買進：{trades.buy:,} 股", f"  賣出：{trades.sell:,} 股", f"  買賣超：{trades.net:,} 股", ""]


def select_type(category: str) -> Optional[str]:
    """T86 selectType for a category: default (no warrants), etf, all, or an industry code."""
    category = category.strip().lower()
    if category in CATEGORIES:
        return CATEGORIES[category]
    return category.upper() if re.fullmatch(r"[0-9a-z]{2,7}", category) else None


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    """Register TWSE listed stocks institutional investor tools."""
    _client = client or TWSEAPIClient.get_instance()

    @mcp.tool
    @handle_api_errors()
    def get_twse_institutional_investors_summary(date: str = "", category: str = "", sort_by: str = "total",
                                                 side: str = "abs", limit: int = DEFAULT_DISPLAY_LIMIT,
                                                 offset: int = 0) -> str:
        """查詢上市「個股」三大法人買賣超排行（單位：股）：例如外資買超前 20 名、投信賣超最多的股票。
        預設最新交易日，可查任意過去交易日；預設排除權證與牛熊證。
        市場整體的法人買賣金額請用 get_market_institutional_amounts_history；
        單一個股的完整明細請用 get_twse_institutional_investors_by_stock；上櫃股票請用 get_otc_institutional。

        回傳：依指定方式排序的個股，每筆含外資、投信、自營商與三大法人合計的買賣超股數

        Args:
            date: 查詢日期 YYYYMMDD（選填，留空＝最新交易日）
            category: 範圍（選填）：留空＝不含權證、牛熊證（含 ETF）；"stock"＝再排除 ETF
                （仍含少數特別股、ETN、受益證券）；"etf"＝只看 ETF；"all"＝含權證；
                或產業代碼，例如 "24"（半導體業）、"28"（電子零組件業）
            sort_by: 依誰的買賣超排序：total（三大法人合計，預設）、foreign（外資，含外資自營商）、
                trust（投信）、dealer（自營商）
            side: buy（只列買超，由大到小）、sell（只列賣超，由大到小）、abs（買超與賣超依絕對值混排，預設）
            limit: 回傳筆數上限（預設 50）
            offset: 跳過前 N 筆（預設 0，搭配 limit 分頁）
        """
        error = check_choice("sort_by", sort_by, SORT_LABELS) or check_choice("side", side, SIDES)
        if error:
            raise ToolError(error)
        category_type = select_type(category)
        if category_type is None:
            raise ToolError("category 必須留空，或是 stock、etf、all、產業代碼（例如 24）")
        day = t86_flows(_client, category_type, date.strip())

        label = date.strip() or "最新交易日"
        if day is None:
            return f"查無 {label} 的三大法人買賣超資料，請確認該日期為交易日（非假日或週末）及 category"
        if not day.flows:
            return f"查無 {label} 的三大法人買賣超資料"

        title = day.title or f"{label} 三大法人買賣超日報"
        flows = day.flows
        if category.strip().lower() == "stock":
            flows = [f for f in flows if not f.code.startswith("00")]
        active = rank(flows, lambda f: f.net(sort_by), side)
        if not active:
            return f"查無 {label} {SORT_LABELS[sort_by]}{SIDES[side]}的個股"

        paged = Page(limit, offset).take(active)
        if paged.past_end:
            return paged.out_of_range(f"{label} {SORT_LABELS[sort_by]}{SIDES[side]}個股")

        header = f"【{title}】依{SORT_LABELS[sort_by]}{SIDES[side]}排序，單位：股（共 {paged.total} 支"
        if paged.span("名"):
            header += f"，{paged.span('名')}"
        header += "）\n"

        lines = [header]
        for f in paged.rows:
            lines.append(
                f"{f.code} {f.name} | 外資: {f.foreign.net:,} | "
                f"投信: {f.trust.net:,} | 自營: {f.dealer.net:,} | 合計: {f.total_net:,}"
            )

        if paged.more():
            lines.append("\n" + paged.more())

        return "\n".join(lines)

    @mcp.tool
    @handle_api_errors()
    def get_twse_institutional_investors_by_stock(stock_no: str, date: str = "") -> str:
        """查詢單一上市股票（或 ETF、權證）某一天的三大法人買賣超完整明細（單位：股）：
        預設最新交易日，可查任意過去交易日。
        要找「哪些股票被法人買超／賣超最多」請用 get_twse_institutional_investors_summary；
        上櫃股票請用 get_otc_institutional(stock_no=...)。

        回傳：外資（不含外資自營商）、外資自營商、投信、自營商（自行買賣／避險）各自的買進、賣出、買賣超股數，
        以及三大法人合計

        Args:
            stock_no: 股票代號，例如 "2330"（台積電）、"0050"（元大台灣50）
            date: 查詢日期 YYYYMMDD（選填，留空＝最新交易日）
        """
        day = t86_flows(_client, "ALL", date.strip())

        label = date.strip() or "最新交易日"
        if day is None:
            return f"查無 {label} 的三大法人買賣超資料，請確認該日期為交易日（非假日或週末）"
        if not day.flows:
            return f"查無 {label} 的三大法人買賣超資料"

        stock_no = stock_no.strip()
        f = next((f for f in day.flows if f.code == stock_no), None)
        if f is None:
            return f"查無上市股票代號 {stock_no} 在 {label} 的三大法人資料（上櫃股票請用 get_otc_institutional）"

        title = day.title or f"{label} 三大法人買賣超日報"
        lines = [f"【{title}】", f"股票代號：{f.code}  股票名稱：{f.name}\n"]
        if f.foreign_ex_dealer is not None:  # 外資自營商 reported separately (T86 since 2017-12-18)
            lines += (_section("─── 外資及陸資（不含外資自營商）───", f.foreign_ex_dealer)
                      + _section("─── 外資自營商 ───", f.foreign_dealer))
        else:
            lines += _section("─── 外資 ───", f.foreign)
        lines += _section("─── 投信 ───", f.trust)
        lines.append("─── 自營商 ───")
        if f.dealer_self is not None:
            for kind, t in (("自行買賣", f.dealer_self), ("避險", f.dealer_hedge)):
                lines += [f"  {kind} 買進：{t.buy:,} 股", f"  {kind} 賣出：{t.sell:,} 股", f"  {kind} 買賣超：{t.net:,} 股"]
            lines.append(f"  合計買賣超：{f.dealer.net:,} 股")
        else:
            lines += [f"  買進：{f.dealer.buy:,} 股", f"  賣出：{f.dealer.sell:,} 股", f"  買賣超：{f.dealer.net:,} 股"]
        lines += ["", "═══ 三大法人合計買賣超 ═══", f"  {f.total_net:,} 股"]

        return "\n".join(lines)
