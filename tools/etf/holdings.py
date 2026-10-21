"""ETF holdings (成分股), every issuer: monthly top 10 or quarterly holdings above 1% of NAV.

Source: SITCA 基金投資明細 (utils/sitca.py) — IN2629 monthly 前十大, IN2630 quarterly
占淨資產 1% 以上. Those pages list fund names only, so the ETF code is first resolved in the
SITCA ETF zone (etf_statement2: 基金名稱 + 類型代號), then the holdings of that class are
searched for the same name after removing disclaimers and share-class suffixes
(utils.sitca.fund_name_key). Exact match only — never fuzzy: 正向2倍 and 反向1倍 funds differ
by two characters.

Checked 2026-08: 318 of 340 ETFs match; every ETF-class fund in IN2629 matches exactly one
ETF. The 22 others are leveraged/inverse ETFs, which IN2629 does not list (they hold futures
and cash). Daily full portfolios (PCF) exist only on each issuer's website and are not used.
"""

from typing import Dict, List, Optional

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from utils import TWSEAPIClient, handle_api_errors
from utils.sitca import (
    HOLDINGS_MONTHLY_PAGE,
    HOLDINGS_QUARTERLY_PAGE,
    available_months,
    fund_name_key,
    holdings_by_class,
    holdings_months,
    query_rows,
    to_number,
)

STATEMENT_PAGE = "etf_statement.aspx"
STATEMENT_RESULT = "etf_statement2.aspx"
# Holdings columns read by name.
COL_RANK = "名次"
COL_KIND = "標的種類"
COL_CODE = "標的代號 或 Bloomberg Isin Code"
COL_NAME = "標的名稱"
COL_AMOUNT = "金額"
COL_PCT = "占基金淨資產價值 之比例(%)"
REQUIRED_COLUMNS = ("基金名稱", COL_KIND, COL_CODE, COL_NAME, COL_AMOUNT, COL_PCT)


def _amount(value: Optional[float]) -> str:
    if value is None:
        return "-"
    return f"{value / 1e8:,.2f} 億元" if abs(value) >= 1e8 else f"{value / 1e4:,.0f} 萬元"


def format_holdings(header: List[str], rows: List[List[str]]) -> List[str]:
    """Holding rows (fund-name column already removed) → ranked text lines."""
    cols = header[1:]
    items: List[Dict[str, str]] = [dict(zip(cols, r)) for r in rows]
    # The quarterly page has no 名次: rank by weight.
    if COL_RANK not in cols:
        items.sort(key=lambda h: to_number(h.get(COL_PCT, "")) or 0, reverse=True)
    lines = []
    for i, h in enumerate(items, 1):
        rank = h.get(COL_RANK) or str(i)
        code = h.get(COL_CODE, "")
        lines.append(
            f"{rank}. {h.get(COL_NAME, '')}{f'（{code}）' if code else ''} | {h.get(COL_KIND, '')} | "
            f"占淨值 {h.get(COL_PCT, '-')}% | 金額 {_amount(to_number(h.get(COL_AMOUNT, '')))}"
        )
    return lines


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    """Register the ETF holdings tool."""
    _client = client or TWSEAPIClient.get_instance()

    @mcp.tool
    @handle_api_errors()
    def get_etf_holdings(code: str, period: str = "", quarterly: bool = False) -> str:
        """查詢 ETF 成分股／持股明細（投信投顧公會「基金投資明細」，涵蓋所有投信、上市與上櫃）。
        預設為每月前十大持股（2021-08 起，約次月第 10 個營業日公布上月資料）；
        quarterly=True 改為每季占基金淨資產 1% 以上的全部持股（2021-09 起）。
        每筆列出標的名稱、代號（台股代號或國外 ISIN）、上市／上櫃／國外等種類、占淨值比例與金額。
        槓桿型、反向型 ETF 多半只持有期貨與現金，不在明細中；期貨 ETF 與外幣級別代號不在投信投顧公會資料中。

        回傳：ETF 名稱、資料期間，以及依名次（季資料依占淨值比例）排列的持股與合計占淨值比例

        Args:
            code: ETF 代號，例如 "0050"、"00878"、"00981A"、"00679B"
            period: 月份 YYYYMM（選填，留空＝最新一期）。quarterly=True 時須為季末月，例如 "202606"
            quarterly: False＝每月前十大（預設）；True＝每季占淨值 1% 以上的全部持股
        """
        code = code.strip().upper()
        if not code:
            raise ToolError("請提供 ETF 代號，例如 0050")
        page = HOLDINGS_QUARTERLY_PAGE if quarterly else HOLDINGS_MONTHLY_PAGE
        months = holdings_months(_client, page)
        period = period.strip()
        if period and period not in months:
            kind = "季末月" if quarterly else "月份"
            raise ToolError(f"period 必須是{kind} YYYYMM，可查 {months[-1]}～{months[0]}")
        ym = period or months[0]

        # The ETF zone gives the fund name and SITCA class the holdings pages are keyed by.
        statement_months = available_months(_client, STATEMENT_PAGE)
        statement = query_rows(_client, STATEMENT_RESULT, statement_months[0], code=code)
        if len(statement) < 2:
            return (f"查無 ETF 代號 {code} 的投信投顧公會資料"
                    "（期貨 ETF、外幣級別代號或尚未公布月報的新 ETF 不在此資料中）")
        info = dict(zip(statement[0], statement[1]))
        # Funds get renamed (兆豐國際臺灣藍籌30 → 兆豐臺灣藍籌30), so for a past period use the
        # name and class the ETF zone shows for that month, found by 基金統編.
        if ym != statement_months[0] and ym in statement_months:
            past = query_rows(_client, STATEMENT_RESULT, ym, fund_id=info.get("基金統編", ""))
            if len(past) >= 2:
                info.update({k: v for k, v in zip(past[0], past[1]) if k in ("基金名稱", "類型代號")})
        fund_name, fund_class = info.get("基金名稱", ""), info.get("類型代號", "")

        header, funds = holdings_by_class(_client, page, ym, fund_class)
        if not header:
            return f"查無 {ym[:4]}-{ym[4:]} 類別 {fund_class} 的基金投資明細"
        missing = [c for c in REQUIRED_COLUMNS if c not in header]
        if missing:
            raise ValueError(f"投信投顧公會基金投資明細欄位已變更，缺少: {missing}")
        target = fund_name_key(fund_name)
        rows = next((r for name, r in funds.items() if fund_name_key(name) == target), None)
        if rows is None:
            return (f"{ym[:4]}-{ym[4:]} 的基金投資明細中沒有 {code} {info.get('證券簡稱', '')}（{fund_name}）。"
                    "槓桿型、反向型 ETF 多半只持有期貨與現金而不列入；新 ETF 要等首次申報後才有資料")

        lines = format_holdings(header, rows)
        total = sum(to_number(dict(zip(header[1:], r)).get(COL_PCT, "")) or 0 for r in rows)
        scope = "每季占淨值 1% 以上持股" if quarterly else "每月前十大持股"
        out = [f"【{code} {info.get('證券簡稱', '')} 持股明細】{fund_name}",
               f"資料期間 {ym[:4]}-{ym[4:]}｜{scope}｜共 {len(lines)} 檔，合計占淨值 {total:.2f}%\n"]
        return "\n".join(out + lines)
