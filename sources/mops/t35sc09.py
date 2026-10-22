"""ajax_t35sc09: 買回自己公司股份（庫藏股）彙總統計表 — every buyback a board resolved on within a date range.

Legacy MOPS page: ``POST mopsov.twse.com.tw/mops/web/ajax_t35sc09`` with ``TYPEK`` (sii / otc / rotc / pub),
``d1`` / ``d2`` (董事會決議日期, ROC ``1150901``) and ``RD=1``. The reply is HTML: a title table, then the
data table under a two-row header (rowspan / colspan)::

    序號 | 公司代號 | 公司名稱 | 董事會決議日期 | 買回目的 | 買回股份總金額上限 | 預定買回股數 | 買回價格區間 | 預定買回期間 | …
                                                                                       最低 | 最高       起 | 迄
    1 | 2303 | 聯電 | 99/02/02 | 1 | 50,561,081,000 | 300,000,000 | 10.95 | 25.85 | 99/02/03 | 99/04/02 | Y | …

Every few hundred rows a new ``<table>`` starts, header repeated; ``utils.mops.parse_html_tables`` splits them.
Headers carry ``<br>`` line breaks and red notes such as (空白為尚在執行中), which are dropped before the
columns are looked up by name. 買回達一定標準資料 is a button, so its cell is empty. Numbers have thousands
separators; the 本次… columns are empty while a buyback is still running. A range without buybacks is a page
saying 查無所需資料. Same 20 columns checked 2005–2026 for 上市, 上櫃 and 公開發行.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import List, Optional, Sequence

from utils.api_client import TWSEAPIClient
from utils.date_helper import roc_date
from utils.errors import UpstreamFormatError
from utils.mops import mops_legacy_post, parse_html_tables
from utils.parse import decimal_or_none, int_or_none

from ..columns import column_index

SOURCE = "t35sc09"
NO_DATA_TEXT = "查無所需資料"
# Notes printed in red under some headers; not part of the column's name.
_NOTES = ("(空白為尚在執行中)", "(依最新財報計算之法定上限)")
# Header cells spanning two columns, and the second header row's names under them.
GROUPS = {"買回價格區間": ("最低", "最高"), "預定買回期間": ("起", "迄")}
FIELDS = ("序號", "公司代號", "公司名稱", "董事會決議日期", "買回目的", "買回股份總金額上限", "預定買回股數",
          "買回價格區間/最低", "買回價格區間/最高", "預定買回期間/起", "預定買回期間/迄", "是否執行完畢",
          "本次已買回股數", "本次執行完畢已註銷或轉讓股數", "本次已買回股數佔預定買回股數比例(%)", "本次已買回總金額",
          "本次平均每股買回價格", "本次買回股數佔公司已發行股份總數比例(%)", "本次未執行完畢之原因")


@dataclass(frozen=True)
class Buyback:
    code: str                            # 公司代號
    name: str                            # 公司名稱
    resolution_date: str                 # 董事會決議日期 as published (ROC "114/04/10", "99/02/02")
    purpose: str                         # 買回目的 code: 1 轉讓股份予員工, 2 股權轉換, 3 維護公司信用及股東權益
    amount_cap: Optional[Decimal]        # 買回股份總金額上限 (元)
    planned_shares: Optional[int]        # 預定買回股數
    price_low: Optional[Decimal]         # 買回價格區間 最低 (元)
    price_high: Optional[Decimal]
    period_start: str                    # 預定買回期間 起, as published (ROC)
    period_end: str
    completed: str                       # 是否執行完畢: Y / N
    bought_shares: Optional[int]         # 本次已買回股數; None while the buyback is still running
    cancelled_shares: Optional[int]      # 本次執行完畢已註銷或轉讓股數
    pct_of_planned: Optional[Decimal]    # 本次已買回股數佔預定買回股數比例 (%)
    bought_amount: Optional[Decimal]     # 本次已買回總金額 (元)
    average_price: Optional[Decimal]     # 本次平均每股買回價格 (元)
    pct_of_issued: Optional[Decimal]     # 本次買回股數佔公司已發行股份總數比例 (%)
    unfinished_reason: str               # 本次未執行完畢之原因 ("" when none)


def _name(cell: str) -> str:
    name = "".join(cell.split())
    for note in _NOTES:
        name = name.replace(note, "")
    return name


def _column_names(top: Sequence[str], sub: Sequence[str]) -> List[str]:
    """One name per data cell from the two header rows: 買回價格區間 → 買回價格區間/最低, 買回價格區間/最高."""
    top_names = [_name(c) for c in top]
    expected = [s for t in top_names if t in GROUPS for s in GROUPS[t]]
    if [_name(c) for c in sub] != expected:
        raise UpstreamFormatError(f"{SOURCE} 第二列表頭已變更：{list(sub)}，預期 {expected}")
    names: List[str] = []
    for t in top_names:
        names += [f"{t}/{s}" for s in GROUPS[t]] if t in GROUPS else [t]
    return names


def treasury_buybacks(client: TWSEAPIClient, market: str, start: str, end: str) -> Optional[List[Buyback]]:
    """Buybacks resolved on from ``start`` to ``end`` (西元 YYYYMMDD) in ``market`` (sii / otc / rotc / pub), in
    MOPS's order, or None when MOPS has none. Raises ``UpstreamFormatError`` on a page without the table (MOPS
    restricting access, or a redesign) or a changed header."""
    html = mops_legacy_post(client, "ajax_t35sc09", {"TYPEK": market, "d1": roc_date(start, sep=""),
                                                     "d2": roc_date(end, sep=""), "RD": "1"})
    if NO_DATA_TEXT in html:
        return None
    rows = [r for table in parse_html_tables(html) for r in table]
    head = next((i for i, r in enumerate(rows) if "公司代號" in map(_name, r)), None)
    if head is None or head + 1 == len(rows):
        raise UpstreamFormatError("公開資訊觀測站回應非預期頁面（可能暫時限制存取或頁面改版），請稍後再試")
    names = _column_names(rows[head], rows[head + 1])
    col = column_index(names, FIELDS, SOURCE)
    seq = col["序號"]
    buybacks = []
    for r in rows:
        if len(r) <= seq or not r[seq].isdigit():
            continue  # titles, headers, 家數合計 and the other totals under the table
        if len(r) != len(names):
            raise UpstreamFormatError(f"{SOURCE} 資料列有 {len(r)} 格，表頭有 {len(names)} 欄：{r}")
        buybacks.append(Buyback(
            code=r[col["公司代號"]],
            name=r[col["公司名稱"]],
            resolution_date=r[col["董事會決議日期"]],
            purpose=r[col["買回目的"]],
            amount_cap=decimal_or_none(r[col["買回股份總金額上限"]]),
            planned_shares=int_or_none(r[col["預定買回股數"]]),
            price_low=decimal_or_none(r[col["買回價格區間/最低"]]),
            price_high=decimal_or_none(r[col["買回價格區間/最高"]]),
            period_start=r[col["預定買回期間/起"]],
            period_end=r[col["預定買回期間/迄"]],
            completed=r[col["是否執行完畢"]],
            bought_shares=int_or_none(r[col["本次已買回股數"]]),
            cancelled_shares=int_or_none(r[col["本次執行完畢已註銷或轉讓股數"]]),
            pct_of_planned=decimal_or_none(r[col["本次已買回股數佔預定買回股數比例(%)"]]),
            bought_amount=decimal_or_none(r[col["本次已買回總金額"]]),
            average_price=decimal_or_none(r[col["本次平均每股買回價格"]]),
            pct_of_issued=decimal_or_none(r[col["本次買回股數佔公司已發行股份總數比例(%)"]]),
            unfinished_reason=r[col["本次未執行完畢之原因"]],
        ))
    return buybacks
