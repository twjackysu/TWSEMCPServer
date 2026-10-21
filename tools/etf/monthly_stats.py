"""ETF monthly scale, holders, creations/redemptions and regular-investment flows.

Source: SITCA ETF zone etf_statement2 (utils/sitca.py), every issuer's domestic ETFs from
2007-01 to last month. One ETF's history is read month by month by 基金統編 because the
older months have no 證券代號 (see utils/sitca.py).
"""

from typing import Dict, List, Literal, Optional

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from utils import TWSEAPIClient
from toolkit import bounded, handle_api_errors
from utils.sitca import available_months, query_rows, to_number

STATEMENT_PAGE = "etf_statement.aspx"
STATEMENT_RESULT = "etf_statement2.aspx"
MAX_MONTHS = 24
MAX_LIST = 100

# Columns read by name (in TWD; the 原幣 columns are 0 for TWD-denominated funds).
COL_SCALE = "基金規模(台幣)"
COL_SHARE = "基金規模市場占有率"
COL_NAV = "單位淨值(台幣)"
COL_UNITS = "受益權單位數"
COL_NATURAL = "自然人受益人數"
COL_LEGAL = "法人受益人數"
COL_HOLDERS = "總受益人數"
COL_SUBSCRIBE = "本月申購總金額(台幣)"
COL_REDEEM = "本月買回總金額(台幣)"
COL_RI_COUNT = "本月定期定額扣款筆數"
COL_RI_ACCOUNTS = "本月定期定額扣款戶數"
COL_RI_AMOUNT = "本月定期定額扣款金額(台幣)"
REQUIRED_COLUMNS = (
    "證券代號", "證券簡稱", "基金統編", "基金名稱", "類型", COL_SCALE, COL_SHARE, COL_NAV, COL_UNITS,
    COL_NATURAL, COL_LEGAL, COL_HOLDERS, COL_SUBSCRIBE, COL_REDEEM, COL_RI_COUNT, COL_RI_ACCOUNTS, COL_RI_AMOUNT,
)

SortBy = Literal["scale", "holders", "net_flow", "regular"]  # SORTS
SORTS = {
    "scale": ("規模", COL_SCALE),
    "holders": ("受益人數", COL_HOLDERS),
    "net_flow": ("淨申購金額", None),
    "regular": ("定期定額扣款金額", COL_RI_AMOUNT),
}


def records(rows: List[List[str]]) -> List[Dict[str, str]]:
    """Result rows → dicts keyed by the header; raise if a column we read is gone."""
    if not rows:
        return []
    header = rows[0]
    missing = [c for c in REQUIRED_COLUMNS if c not in header]
    if missing:
        raise ValueError(f"投信投顧公會 ETF 月報欄位已變更，缺少: {missing}")
    return [dict(zip(header, r, strict=False)) for r in rows[1:]]


def _num(r: Dict[str, str], col: str) -> float:
    return to_number(r.get(col, "")) or 0.0


def net_flow(r: Dict[str, str]) -> float:
    return _num(r, COL_SUBSCRIBE) - _num(r, COL_REDEEM)


def _yi(value: float, signed: bool = False) -> str:
    return f"{value / 1e8:+,.1f} 億" if signed else f"{value / 1e8:,.1f} 億"


def format_month(ym: str, r: Dict[str, str], prev: Optional[Dict[str, str]] = None) -> str:
    holders = _num(r, COL_HOLDERS)
    line = (
        f"{ym[:4]}-{ym[4:]} | 規模 {_yi(_num(r, COL_SCALE))}（市占 {r.get(COL_SHARE, '-')}）| "
        f"淨值 {r.get(COL_NAV, '-')} | 受益權單位數 {_num(r, COL_UNITS):,.0f} | "
        f"受益人數 {holders:,.0f}（自然人 {_num(r, COL_NATURAL):,.0f}／法人 {_num(r, COL_LEGAL):,.0f}）"
    )
    if prev is not None:
        line += f"，較前月 {holders - _num(prev, COL_HOLDERS):+,.0f}"
    line += (
        f" | 申購 {_yi(_num(r, COL_SUBSCRIBE))}／買回 {_yi(_num(r, COL_REDEEM))}（淨 {_yi(net_flow(r), True)}）| "
        f"定期定額 {_num(r, COL_RI_COUNT):,.0f} 筆、{_num(r, COL_RI_ACCOUNTS):,.0f} 戶、{_yi(_num(r, COL_RI_AMOUNT))}"
    )
    return line


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    """Register the ETF monthly statistics tool."""
    _client = client or TWSEAPIClient.get_instance()

    def _history(code: str, all_months: List[str], start: int, months: int) -> str:
        # Resolve the code to its 基金統編 in the newest month: older months have no 證券代號.
        found = records(query_rows(_client, STATEMENT_RESULT, all_months[0], code=code))
        if not found:
            return f"查無 ETF 代號 {code} 的投信投顧公會月報資料（期貨 ETF、外幣級別或尚未公布月報的新 ETF 不在此資料中）"
        latest = found[0]
        fund_id, share_class = latest["基金統編"], latest["類型"]

        series = []
        for ym in all_months[start:start + months]:
            rows = [latest] if ym == all_months[0] else records(query_rows(_client, STATEMENT_RESULT, ym, fund_id=fund_id))
            # A fund with several share classes has one row per class.
            row = next((r for r in rows if r["證券代號"] == code), None) \
                or next((r for r in rows if r["類型"] == share_class), None) \
                or (rows[0] if len(rows) == 1 else None)
            if row is None:
                break  # before the fund existed
            series.append((ym, row))
        if not series:
            return f"{code} 在 {all_months[start][:4]}-{all_months[start][4:]} 尚無月報資料"

        lines = [f"【{code} {latest['證券簡稱']} 每月統計】{latest['基金名稱']}（共 {len(series)} 個月，由新到舊）\n"]
        for i, (ym, row) in enumerate(series):
            lines.append(format_month(ym, row, series[i + 1][1] if i + 1 < len(series) else None))
        return "\n".join(lines)

    @mcp.tool
    @handle_api_errors()
    def get_etf_monthly_stats(code: str = "", months: bounded(1, MAX_MONTHS) = 6, period: str = "",
                              sort_by: SortBy = "scale", limit: bounded(1, MAX_LIST) = 30) -> str:
        """查詢 ETF 每月統計（投信投顧公會月報，涵蓋所有投信、上市與上櫃）：基金規模與市占、
        單位淨值、受益權單位數、受益人數（自然人／法人）、當月申購與買回金額、定期定額扣款
        筆數／戶數／金額。資料自 2007 年起，通常於次月中旬公布上月資料。
        指定 code 時列出該 ETF 逐月趨勢；不指定時列出單月全市場排行。

        回傳：每月（或每檔）的規模、市占、淨值、單位數、受益人數、申購買回與定期定額資料

        Args:
            code: ETF 代號，例如 "0050"、"00679B"（留空＝單月排行）
            months: 指定 code 時的月數（預設 6，最多 24；每多一個月多一次查詢，約 2–4 秒）
            period: 月份 西元 YYYYMM（選填，留空＝最新一個月）。指定 code 時為趨勢的最新月份
            sort_by: 排行依據：scale（規模，預設）、holders（受益人數）、net_flow（淨申購金額）、
                regular（定期定額扣款金額）
            limit: 排行筆數（預設 30，最多 100）
        """
        all_months = available_months(_client, STATEMENT_PAGE)
        period = period.strip()
        if period and period not in all_months:
            raise ToolError(f"period 必須是 YYYYMM 且介於 {all_months[-1]}～{all_months[0]}")
        start = all_months.index(period) if period else 0

        code = code.strip().upper()
        if code:
            return _history(code, all_months, start, months)

        ym = all_months[start]
        rows = records(query_rows(_client, STATEMENT_RESULT, ym))
        if not rows:
            return f"查無 {ym[:4]}-{ym[4:]} 的 ETF 月報資料"
        label, col = SORTS[sort_by]
        ranked = sorted(rows, key=(lambda r: _num(r, col)) if col else net_flow, reverse=True)[:limit]
        lines = [f"【ETF {label}排行】{ym[:4]}-{ym[4:]}（共 {len(rows)} 檔，列出前 {len(ranked)} 檔）\n"]
        for i, r in enumerate(ranked, 1):
            ident = f"{r['證券代號']} {r['證券簡稱']}" if r["證券代號"] != "-" else r["基金名稱"]
            lines.append(f"{i}. {ident} | " + format_month(ym, r).split(" | ", 1)[1])
        return "\n".join(lines)
