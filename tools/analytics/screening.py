"""選股 screener and 同業比較 over listed + OTC stocks, from the latest-day valuation and price
snapshot (see utils/market_snapshot.py)."""

from statistics import median
from typing import List, Optional
from fastmcp import FastMCP
from utils import TWSEAPIClient, handle_api_errors, format_list_response
from utils.market_snapshot import LISTED, OTC, StockSnapshot, industry_members, industry_of, market_snapshot

MARKETS = {"all": (LISTED, OTC), "listed": (LISTED,), "otc": (OTC,)}
# sort key → (attribute, descending)
SORTS = {"yield": ("dividend_yield", True), "pe": ("pe", False), "pb": ("pb", False),
         "change": ("change_pct", True), "volume": ("volume", True)}


def _fmt(v: Optional[float], suffix: str = "") -> str:
    return "-" if v is None else f"{v:,.2f}{suffix}"


def format_row(s: StockSnapshot, marker: str = "") -> str:
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

    @mcp.tool
    @handle_api_errors()
    def get_stock_screener(market: str = "all", industry: str = "", same_industry_as: str = "",
                           pe_min: float = 0, pe_max: float = 0, pb_max: float = 0, yield_min: float = 0,
                           sort_by: str = "yield", limit: int = 30, offset: int = 0) -> str:
        """依估值條件篩選上市／上櫃股票（最新交易日）：本益比區間、股價淨值比上限、殖利率下限，
        可限定產業。條件填 0 代表不設限；設定本益比條件時，本益比為空（虧損）的公司會被排除。

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
            limit: 回傳筆數上限（預設 30）
            offset: 跳過前 N 筆（預設 0，搭配 limit 分頁）

        Returns:
            符合條件的股票代號、名稱、市場、收盤價、漲跌幅、本益比、股價淨值比、殖利率
        """
        markets = MARKETS.get(market.strip().lower())
        if markets is None:
            return f"market 只能是 {', '.join(MARKETS)}"
        if sort_by not in SORTS:
            return f"sort_by 只能是 {', '.join(SORTS)}"

        snapshot, as_of = market_snapshot(_client, markets)
        rows = list(snapshot.values())
        scope = []
        industry = industry.strip()
        if same_industry_as.strip():
            industry = industry_of(_client, same_industry_as.strip()) or ""
            if not industry:
                return f"查無 {same_industry_as} 的產業別"
        if industry:
            name, members = industry_members(_client, industry)
            rows = [s for s in rows if s.code in set(members)]
            scope.append(f"產業 {industry} {name}".strip())

        if pe_min or pe_max:
            rows = [s for s in rows if s.pe is not None and s.pe >= pe_min and (not pe_max or s.pe <= pe_max)]
            scope.append(f"本益比 {pe_min or ''}～{pe_max or ''}")
        if pb_max:
            rows = [s for s in rows if s.pb is not None and s.pb <= pb_max]
            scope.append(f"淨值比 ≤ {pb_max}")
        if yield_min:
            rows = [s for s in rows if s.dividend_yield is not None and s.dividend_yield >= yield_min]
            scope.append(f"殖利率 ≥ {yield_min}%")

        rows = sort_rows(rows, sort_by)
        label = (f" {'、'.join(scope) or '全部'} 的{'上市+上櫃' if len(markets) == 2 else markets[0]}股票"
                 f"（資料日 {as_of}，依 {sort_by} 排序）")
        return format_list_response(rows, label, format_row, limit, offset)

    @mcp.tool
    @handle_api_errors(use_code_param=True)
    def get_industry_peers(code: str, sort_by: str = "pe", limit: int = 30) -> str:
        """同業比較：找出與指定股票同產業的上市、上櫃公司（最新交易日），並列本益比、淨值比、
        殖利率、漲跌幅，附產業中位數與該股的排名位置。

        Args:
            code: 股票代號，例如 "2330"
            sort_by: pe（本益比低→高，預設）、pb、yield、change、volume
            limit: 列出的同業家數上限（預設 30；該股一定會列出）

        Returns:
            產業名稱、同業家數、本益比／淨值比／殖利率中位數、該股在各指標的排名，以及同業清單（▶ 標示該股）
        """
        code = code.strip()
        if sort_by not in SORTS:
            return f"sort_by 只能是 {', '.join(SORTS)}"
        industry = industry_of(_client, code)
        if not industry:
            return f"查無 {code} 的產業別（僅支援上市、上櫃公司）"
        name, members = industry_members(_client, industry)
        snapshot, as_of = market_snapshot(_client)
        peers = [snapshot[c] for c in dict.fromkeys(members) if c in snapshot]
        target = snapshot.get(code)
        if not peers or target is None:
            return f"查無 {code} 所屬產業 {industry} 的同業資料"

        def med(attr):
            values = [getattr(s, attr) for s in peers if getattr(s, attr) is not None]
            return median(values) if values else None

        def rank(attr, low_first):
            values = sorted((s for s in peers if getattr(s, attr) is not None),
                            key=lambda s: getattr(s, attr), reverse=not low_first)
            pos = next((i for i, s in enumerate(values) if s.code == code), None)
            return "-" if pos is None else f"{pos + 1}/{len(values)}"

        ordered = sort_rows(peers, sort_by)
        shown = ordered[:limit]
        if target not in shown:
            shown.append(target)
        lines = [
            f"【{target.name}({code}) 同業比較：產業 {industry} {name}】（上市+上櫃共 {len(peers)} 家，資料日 {as_of}）",
            f"產業中位數：本益比 {_fmt(med('pe'))} | 淨值比 {_fmt(med('pb'))} | 殖利率 {_fmt(med('dividend_yield'), '%')}",
            f"{target.name} 排名：本益比由低到高 {rank('pe', True)} | 淨值比由低到高 {rank('pb', True)} | "
            f"殖利率由高到低 {rank('dividend_yield', False)}",
            "",
        ]
        lines += [format_row(s, "▶ " if s.code == code else "  ").rstrip("\n") for s in shown]
        if len(ordered) > limit:
            lines.append(f"\n...其餘 {len(ordered) - limit} 家未列出（可調高 limit）")
        return "\n".join(lines)
