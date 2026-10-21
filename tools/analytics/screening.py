"""選股 screener and 同業比較 over listed + OTC stocks, from the latest-day valuation and price
snapshot (see services/market_snapshot.py).

Both reply with text and with the same data as structured content (``ScreenerResult``,
``PeerComparison``; see toolkit/structured.py)."""

from dataclasses import dataclass
from datetime import date, datetime
from statistics import median
from typing import Annotated, List, Literal, Optional

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.tools import ToolResult
from pydantic import Field

from utils import Page, TWSEAPIClient, format_list_response
from toolkit import Offset, bounded, handle_api_errors, output_schema, structured_reply
from services.market_snapshot import (LISTED, OTC, StockSnapshot, data_date_label, industry_members, industry_of,
                                      market_snapshot)

Market = Literal["all", "listed", "otc"]  # MARKETS
MARKETS = {"all": (LISTED, OTC), "listed": (LISTED,), "otc": (OTC,)}
# sort key → (attribute, descending)
SortBy = Literal["yield", "pe", "pb", "change", "volume"]  # SORTS
SORTS = {"yield": ("dividend_yield", True), "pe": ("pe", False), "pb": ("pb", False),
         "change": ("change_pct", True), "volume": ("volume", True)}
# Structured replies are not cut by the response cap, so the row count is bounded here: 500 stocks
# are about 70 KB of text and 130 KB of structured content.
MAX_ROWS = 500


@dataclass(frozen=True)
class StockValuation:
    """一檔股票在最新交易日的行情與估值。"""

    code: Annotated[str, Field(description="股票代號")]
    name: Annotated[str, Field(description="公司簡稱")]
    market: Annotated[str, Field(description="上市 或 上櫃")]
    close: Annotated[Optional[float], Field(description="收盤價（元）")]
    change: Annotated[Optional[float], Field(description="漲跌（元，下跌為負）")]
    change_pct: Annotated[Optional[float], Field(description="漲跌幅（%，下跌為負）")]
    pe: Annotated[Optional[float], Field(description="本益比；虧損或無資料為 null")]
    pb: Annotated[Optional[float], Field(description="股價淨值比")]
    dividend_yield: Annotated[Optional[float], Field(description="殖利率（%）")]
    dividend_year: Annotated[str, Field(description="殖利率所用的股利年度（民國年，例如 114）；空字串＝無")]
    fiscal: Annotated[str, Field(description="本益比、淨值比所用的財報年／季（民國，上市如 115/2、上櫃如 115Q2）；空字串＝無")]
    volume: Annotated[Optional[float], Field(description="成交量（股）")]

    @classmethod
    def of(cls, s: StockSnapshot) -> "StockValuation":
        return cls(s.code, s.name, s.market, s.close, s.change, s.change_pct, s.pe, s.pb, s.dividend_yield,
                   s.dividend_year, s.fiscal, s.volume)


ListedDate = Annotated[Optional[date], Field(description="上市資料日（西元）；未查上市或無資料為 null")]
OtcDate = Annotated[Optional[date], Field(description="上櫃資料日（西元）；未查上櫃或無資料為 null")]


@dataclass(frozen=True)
class ScreenerResult:
    """符合篩選條件的股票（本頁），依 sort_by 排序。"""

    listed_date: ListedDate
    otc_date: OtcDate
    industry: Annotated[str, Field(description="限定的產業代碼（兩位數）；空字串＝不限產業")]
    industry_name: Annotated[str, Field(description="限定的產業名稱；空字串＝不限產業")]
    sort_by: Annotated[str, Field(description="排序依據（yield、pe、pb、change、volume）")]
    total: Annotated[int, Field(description="符合條件的股票數（分頁前）")]
    offset: Annotated[int, Field(description="本頁第一筆在全部結果中的位置（0 起算）")]
    stocks: Annotated[List[StockValuation], Field(description="本頁的股票，依 sort_by 排序；該指標為 null 的排在最後")]


@dataclass(frozen=True)
class Rank:
    """該股在有此指標的同業中的名次。"""

    position: Annotated[int, Field(description="名次（1 起算）")]
    of: Annotated[int, Field(description="有此指標的同業家數")]


@dataclass(frozen=True)
class PeerComparison:
    """一檔股票與同產業上市、上櫃公司的比較。"""

    code: Annotated[str, Field(description="股票代號")]
    name: Annotated[str, Field(description="公司簡稱")]
    industry: Annotated[str, Field(description="產業代碼（兩位數）")]
    industry_name: Annotated[str, Field(description="產業名稱")]
    listed_date: ListedDate
    otc_date: OtcDate
    peer_count: Annotated[int, Field(description="上市＋上櫃同業家數（含該股）")]
    median_pe: Annotated[Optional[float], Field(description="同業本益比中位數")]
    median_pb: Annotated[Optional[float], Field(description="同業股價淨值比中位數")]
    median_dividend_yield: Annotated[Optional[float], Field(description="同業殖利率中位數（%）")]
    pe_rank: Annotated[Optional[Rank], Field(description="本益比由低到高的名次；該股無本益比為 null")]
    pb_rank: Annotated[Optional[Rank], Field(description="股價淨值比由低到高的名次；該股無淨值比為 null")]
    dividend_yield_rank: Annotated[Optional[Rank], Field(description="殖利率由高到低的名次；該股無殖利率為 null")]
    sort_by: Annotated[str, Field(description="peers 的排序依據（yield、pe、pb、change、volume）")]
    peers: Annotated[List[StockValuation], Field(description="依 sort_by 排序的前 limit 家同業；該股不在其中時附在最後")]
    not_shown: Annotated[int, Field(description="排序在 limit 之後、未列出的同業家數")]


def _day(text: Optional[str]) -> Optional[date]:
    try:
        return datetime.strptime(text or "", "%Y%m%d").date()
    except ValueError:
        return None


def _fmt(v: Optional[float], suffix: str = "") -> str:
    return "-" if v is None else f"{v:,.2f}{suffix}"


def format_row(s: StockValuation, marker: str = "") -> str:
    return (
        f"{marker}{s.code} {s.name}（{s.market}）| 收盤:{_fmt(s.close)} 漲跌:{_fmt(s.change_pct, '%')} | "
        f"本益比:{_fmt(s.pe)} 淨值比:{_fmt(s.pb)} 殖利率:{_fmt(s.dividend_yield, '%')}"
        f"（股利年度 {s.dividend_year or '-'}，財報 {s.fiscal or '-'}）\n"
    )


def sort_rows(rows: List[StockSnapshot], sort_by: str) -> List[StockSnapshot]:
    """Sort by the chosen metric; stocks without that metric go last."""
    attr, desc = SORTS[sort_by]
    have = [s for s in rows if getattr(s, attr) is not None]
    missing = [s for s in rows if getattr(s, attr) is None]
    return sorted(have, key=lambda s: getattr(s, attr), reverse=desc) + missing


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    _client = client or TWSEAPIClient.get_instance()

    @mcp.tool(output_schema=output_schema(ScreenerResult))
    @handle_api_errors()
    def get_stock_screener(market: Market = "all", industry: str = "", same_industry_as: str = "",
                           pe_min: float = 0, pe_max: float = 0, pb_max: float = 0, yield_min: float = 0,
                           sort_by: SortBy = "yield", limit: bounded(1, MAX_ROWS) = 30,
                           offset: Offset = 0) -> ToolResult:
        """依估值條件篩選上市／上櫃股票（最新交易日）：本益比區間、股價淨值比上限、殖利率下限，
        可限定產業。條件填 0 代表不設限；設定本益比條件時，本益比為空（虧損）的公司會被排除。

        回傳：符合條件的股票代號、名稱、市場、收盤價、漲跌幅、本益比、股價淨值比、殖利率

        Args:
            market: all＝上市+上櫃（預設）、listed＝上市、otc＝上櫃
            industry: 產業代碼（選填，兩位數，例如 "24" 半導體、"28" 電子零組件、"17" 金融保險；
                可由 get_company_profile 的「產業別」得知）
            same_industry_as: 股票代號（選填），限定為與該股同產業，例如 "2330"
            pe_min: 本益比下限（0＝不設限）
            pe_max: 本益比上限（0＝不設限）
            pb_max: 股價淨值比上限（0＝不設限）
            yield_min: 殖利率下限 %（0＝不設限），例如 5
            sort_by: 排序：yield（殖利率高→低，預設）、pe（本益比低→高）、pb（淨值比低→高）、
                change（當日漲跌幅高→低）、volume（成交量大→小）
            limit: 回傳筆數上限（預設 30，最多 500）
            offset: 跳過前 N 筆（預設 0，搭配 limit 分頁）
        """
        markets = MARKETS[market]

        snapshot, days = market_snapshot(_client, markets)
        rows = list(snapshot.values())
        scope = []
        industry = industry.strip()
        industry_name = ""
        if same_industry_as.strip():
            industry = industry_of(_client, same_industry_as.strip()) or ""
            if not industry:
                raise ToolError(f"查無 {same_industry_as} 的產業別")
        if industry:
            industry_name, members = industry_members(_client, industry)
            rows = [s for s in rows if s.code in set(members)]
            scope.append(f"產業 {industry} {industry_name}".strip())

        if pe_min or pe_max:
            rows = [s for s in rows if s.pe is not None and s.pe >= pe_min and (not pe_max or s.pe <= pe_max)]
            scope.append(f"本益比 {pe_min or ''}～{pe_max or ''}")
        if pb_max:
            rows = [s for s in rows if s.pb is not None and s.pb <= pb_max]
            scope.append(f"淨值比 ≤ {pb_max}")
        if yield_min:
            rows = [s for s in rows if s.dividend_yield is not None and s.dividend_yield >= yield_min]
            scope.append(f"殖利率 ≥ {yield_min}%")

        rows = [StockValuation.of(s) for s in sort_rows(rows, sort_by)]
        label = (f" {'、'.join(scope) or '全部'} 的{'上市+上櫃' if len(markets) == 2 else markets[0]}股票"
                 f"（資料日 {data_date_label(days)}，依 {sort_by} 排序）")
        paged = Page(limit, offset).take(rows)
        result = ScreenerResult(_day(days.get(LISTED)), _day(days.get(OTC)), industry, industry_name, sort_by,
                                len(rows), offset, [] if paged.past_end else paged.rows)
        return structured_reply(format_list_response(rows, label, format_row, limit, offset), result)

    @mcp.tool(output_schema=output_schema(PeerComparison))
    @handle_api_errors(use_code_param=True)
    def get_industry_peers(code: str, sort_by: SortBy = "pe", limit: bounded(1, MAX_ROWS) = 30) -> ToolResult:
        """同業比較：找出與指定股票同產業的上市、上櫃公司（最新交易日），並列本益比、淨值比、
        殖利率、漲跌幅，附產業中位數與該股的排名位置。

        回傳：產業名稱、同業家數、本益比／淨值比／殖利率中位數、該股在各指標的排名，以及同業清單（▶ 標示該股）

        Args:
            code: 股票代號，例如 "2330"
            sort_by: pe（本益比低→高，預設）、pb、yield、change、volume
            limit: 列出的同業家數上限（預設 30，最多 500；該股一定會列出）
        """
        code = code.strip()
        industry = industry_of(_client, code)
        if not industry:
            raise ToolError(f"查無 {code} 的產業別（僅支援上市、上櫃公司）")
        name, members = industry_members(_client, industry)
        snapshot, days = market_snapshot(_client)
        peers = [snapshot[c] for c in dict.fromkeys(members) if c in snapshot]
        target = snapshot.get(code)
        if not peers or target is None:
            raise ToolError(f"查無 {code} 所屬產業 {industry} 的同業資料")

        def med(attr):
            values = [getattr(s, attr) for s in peers if getattr(s, attr) is not None]
            return median(values) if values else None

        def rank(attr, low_first) -> Optional[Rank]:
            values = sorted((s for s in peers if getattr(s, attr) is not None),
                            key=lambda s: getattr(s, attr), reverse=not low_first)
            pos = next((i for i, s in enumerate(values) if s.code == code), None)
            return None if pos is None else Rank(pos + 1, len(values))

        ordered = sort_rows(peers, sort_by)
        shown = ordered[:limit]
        if target not in shown:
            shown.append(target)
        result = PeerComparison(
            code, target.name, industry, name, _day(days.get(LISTED)), _day(days.get(OTC)), len(peers),
            med("pe"), med("pb"), med("dividend_yield"), rank("pe", True), rank("pb", True),
            rank("dividend_yield", False), sort_by, [StockValuation.of(s) for s in shown],
            max(len(ordered) - limit, 0),
        )

        def place(r: Optional[Rank]) -> str:
            return "-" if r is None else f"{r.position}/{r.of}"

        lines = [
            f"【{result.name}({code}) 同業比較：產業 {industry} {name}】"
            f"（上市+上櫃共 {result.peer_count} 家，資料日 {data_date_label(days)}）",
            f"產業中位數：本益比 {_fmt(result.median_pe)} | 淨值比 {_fmt(result.median_pb)} | "
            f"殖利率 {_fmt(result.median_dividend_yield, '%')}",
            f"{result.name} 排名：本益比由低到高 {place(result.pe_rank)} | 淨值比由低到高 {place(result.pb_rank)} | "
            f"殖利率由高到低 {place(result.dividend_yield_rank)}",
            "",
        ]
        lines += [format_row(s, "▶ " if s.code == code else "  ").rstrip("\n") for s in result.peers]
        if result.not_shown:
            lines.append(f"\n...其餘 {result.not_shown} 家未列出（可調高 limit）")
        return structured_reply("\n".join(lines), result)
