"""TWSE listed stocks institutional (三大法人) trading data, per stock (T86, shares).

``selectType``: ALL is every security — ~18,600 of the ~20,000 rows are warrants / CBBCs —
ALLBUT0999 excludes those (~1,300 rows), 0099P is ETFs only, and a two-digit industry code
(e.g. 24 半導體業) one industry. Without ``date`` T86 returns the latest trading day.
"""

import re
from typing import Optional
from fastmcp import FastMCP
from utils import TWSEAPIClient, handle_api_errors, DEFAULT_DISPLAY_LIMIT, MSG_OFFSET_OUT_OF_RANGE
from utils.institutional import SIDES, SORT_LABELS, check_choice, rank

T86_URL = "https://www.twse.com.tw/rwd/zh/fund/T86"
# "stock" is ALLBUT0999 minus ETFs: on both markets every ETF code starts with 00 and every
# 00 code is an ETF (checked 2026-10-16 against T86 0099P and TPEx sect EE).
CATEGORIES = {"": "ALLBUT0999", "stock": "ALLBUT0999", "etf": "0099P", "all": "ALL"}

# Column indices in the data array (based on T86 fields)
IDX_CODE = 0          # 證券代號
IDX_NAME = 1          # 證券名稱
IDX_FK_BUY = 2        # 外陸資買進股數(不含外資自營商)
IDX_FK_SELL = 3       # 外陸資賣出股數(不含外資自營商)
IDX_FK_NET = 4        # 外陸資買賣超股數(不含外資自營商)
IDX_FKDL_BUY = 5      # 外資自營商買進股數
IDX_FKDL_SELL = 6     # 外資自營商賣出股數
IDX_FKDL_NET = 7      # 外資自營商買賣超股數
IDX_IT_BUY = 8        # 投信買進股數
IDX_IT_SELL = 9       # 投信賣出股數
IDX_IT_NET = 10       # 投信買賣超股數
IDX_DL_NET = 11       # 自營商買賣超股數
IDX_DL_BUY_SELF = 12  # 自營商買進股數(自行買賣)
IDX_DL_SELL_SELF = 13 # 自營商賣出股數(自行買賣)
IDX_DL_NET_SELF = 14  # 自營商買賣超股數(自行買賣)
IDX_DL_BUY_HEDGE = 15 # 自營商買進股數(避險)
IDX_DL_SELL_HEDGE = 16# 自營商賣出股數(避險)
IDX_DL_NET_HEDGE = 17 # 自營商買賣超股數(避險)
IDX_TOTAL_NET = 18    # 三大法人買賣超股數


def _parse_num(value: str) -> int:
    """Convert comma-separated number string to int."""
    try:
        return int(value.replace(",", ""))
    except (ValueError, AttributeError):
        return 0


def _fmt(value: str) -> str:
    """Return value as-is (keep original formatted string)."""
    return value or "-"


def net_by(row: list, sort_by: str) -> int:
    """A T86 row's net shares for one investor group; 外資 includes 外資自營商."""
    if sort_by == "foreign":
        return _parse_num(row[IDX_FK_NET]) + _parse_num(row[IDX_FKDL_NET])
    if sort_by == "trust":
        return _parse_num(row[IDX_IT_NET])
    if sort_by == "dealer":
        return _parse_num(row[IDX_DL_NET])
    return _parse_num(row[IDX_TOTAL_NET])


def select_type(category: str) -> Optional[str]:
    """T86 selectType for a category: default (no warrants), etf, all, or an industry code."""
    category = category.strip().lower()
    if category in CATEGORIES:
        return CATEGORIES[category]
    return category.upper() if re.fullmatch(r"[0-9a-z]{2,7}", category) else None


def _params(date: str, category_type: str) -> dict:
    params = {"response": "json", "selectType": category_type}
    if date.strip():
        params["date"] = date.strip()
    return params


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
            return error
        category_type = select_type(category)
        if category_type is None:
            return "category 必須留空，或是 stock、etf、all、產業代碼（例如 24）"
        resp = _client.fetch_json(T86_URL, params=_params(date, category_type))

        label = date.strip() or "最新交易日"
        if not resp or resp.get("stat") != "OK":
            return f"查無 {label} 的三大法人買賣超資料，請確認該日期為交易日（非假日或週末）及 category"

        data = resp.get("data", [])
        if not data:
            return f"查無 {label} 的三大法人買賣超資料"

        title = resp.get("title", f"{label} 三大法人買賣超日報")

        # Some rows (e.g. bond ETFs) have fewer than 19 columns — skip them
        rows = [row for row in data if len(row) > IDX_TOTAL_NET]
        if category.strip().lower() == "stock":
            rows = [row for row in rows if not row[IDX_CODE].strip().startswith("00")]
        active = rank(rows, lambda r: net_by(r, sort_by), side)
        if not active:
            return f"查無 {label} {SORT_LABELS[sort_by]}{SIDES[side]}的個股"

        total = len(active)
        page_data = active[offset:offset + limit]
        if not page_data:
            return MSG_OFFSET_OUT_OF_RANGE.format(
                offset=offset, data_type=f"{label} {SORT_LABELS[sort_by]}{SIDES[side]}個股", count=total
            )
        end = min(offset + limit, total)

        header = f"【{title}】依{SORT_LABELS[sort_by]}{SIDES[side]}排序，單位：股（共 {total} 支"
        if total > limit or offset > 0:
            header += f"，顯示第 {offset + 1}–{end} 名"
        header += "）\n"

        lines = [header]
        for row in page_data:
            lines.append(
                f"{row[IDX_CODE]} {row[IDX_NAME].strip()} | 外資: {net_by(row, 'foreign'):,} | "
                f"投信: {_fmt(row[IDX_IT_NET])} | 自營: {_fmt(row[IDX_DL_NET])} | 合計: {_fmt(row[IDX_TOTAL_NET])}"
            )

        remaining = total - offset - limit
        if remaining > 0:
            lines.append(f"\n...還有 {remaining} 筆，使用 offset={offset + limit} 查看更多")

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
        resp = _client.fetch_json(T86_URL, params=_params(date, "ALL"))

        label = date.strip() or "最新交易日"
        if not resp or resp.get("stat") != "OK":
            return f"查無 {label} 的三大法人買賣超資料，請確認該日期為交易日（非假日或週末）"

        data = resp.get("data", [])
        if not data:
            return f"查無 {label} 的三大法人買賣超資料"

        # Filter by stock code; skip rows with insufficient columns
        stock_no = stock_no.strip()
        row = next((r for r in data if len(r) > IDX_TOTAL_NET and r[IDX_CODE].strip() == stock_no), None)
        if not row:
            return f"查無上市股票代號 {stock_no} 在 {label} 的三大法人資料（上櫃股票請用 get_otc_institutional）"

        title = resp.get("title", f"{label} 三大法人買賣超日報")
        name = row[IDX_NAME]

        lines = [
            f"【{title}】",
            f"股票代號：{row[IDX_CODE]}  股票名稱：{name}\n",
            "─── 外資及陸資（不含外資自營商）───",
            f"  買進：{_fmt(row[IDX_FK_BUY])} 股",
            f"  賣出：{_fmt(row[IDX_FK_SELL])} 股",
            f"  買賣超：{_fmt(row[IDX_FK_NET])} 股",
            "",
            "─── 外資自營商 ───",
            f"  買進：{_fmt(row[IDX_FKDL_BUY])} 股",
            f"  賣出：{_fmt(row[IDX_FKDL_SELL])} 股",
            f"  買賣超：{_fmt(row[IDX_FKDL_NET])} 股",
            "",
            "─── 投信 ───",
            f"  買進：{_fmt(row[IDX_IT_BUY])} 股",
            f"  賣出：{_fmt(row[IDX_IT_SELL])} 股",
            f"  買賣超：{_fmt(row[IDX_IT_NET])} 股",
            "",
            "─── 自營商 ───",
            f"  自行買賣 買進：{_fmt(row[IDX_DL_BUY_SELF])} 股",
            f"  自行買賣 賣出：{_fmt(row[IDX_DL_SELL_SELF])} 股",
            f"  自行買賣 買賣超：{_fmt(row[IDX_DL_NET_SELF])} 股",
            f"  避險 買進：{_fmt(row[IDX_DL_BUY_HEDGE])} 股",
            f"  避險 賣出：{_fmt(row[IDX_DL_SELL_HEDGE])} 股",
            f"  避險 買賣超：{_fmt(row[IDX_DL_NET_HEDGE])} 股",
            f"  合計買賣超：{_fmt(row[IDX_DL_NET])} 股",
            "",
            "═══ 三大法人合計買賣超 ═══",
            f"  {_fmt(row[IDX_TOTAL_NET])} 股",
        ]

        return "\n".join(lines)
