"""MOPS stapap1 (董監事持股餘額明細) and query6_1 (內部人持股異動), the latest month or a given one.

Both take ``POST https://mops.twse.com.tw/mops/api/<page>`` with ``{"companyId", "dataType": "1" (latest) or "2",
"year" (ROC), "month" ("01"), "subsidiaryCompanyId": ""}``.

- stapap1 answers ``{"parentCompany": {"titles", "data", "total", "yymm", "companyAbbreviation", "note", "reason"},
  "subsidiary": …}``: 職稱, 姓名, then holdings and pledges ("118,587,914", "0.00%"); ``total`` holds each director
  category's [持股, 設質股數, 設質比例]. The tool shows the columns as published, so they stay strings.
- query6_1 answers ``{"titles", "data", "year", "month", "companyAbbreviation", …}``: 身份別, 姓名, 持股種類, 選任當時持有股數,
  上月實際持有股數, …, then two groups of five, 本月增加 and 本月減少 (自有股數(集中), …, 設定質權股數 / 解除質權股數),
  then 本月實際自有持有股數, …, 截至本月底累計設質, …. The groups repeat their column names, so columns are found by the
  flattened title ("本月減少 自有股數(集中)"); one title ends with a line break, which flattening strips.

Same titles checked 2010–2026.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from utils.api_client import TWSEAPIClient
from utils.errors import UpstreamFormatError
from utils.mops import flatten_titles, mops_post
from utils.parse import int_or_none

from ..columns import column_index

CHANGE_GROUPS = ("本月增加", "本月減少")


@dataclass(frozen=True)
class BoardHolding:
    title: str                   # 職稱 ("董事長本人")
    name: str                    # 姓名
    values: Tuple[str, ...]      # every other column as published, in BoardHoldings.columns order


@dataclass(frozen=True)
class BoardHoldings:
    name: str                    # companyAbbreviation
    yymm: str                    # ROC year and month as published ("11509")
    columns: Tuple[str, ...]     # flattened titles after 職稱 and 姓名
    holdings: List[BoardHolding]
    totals: Dict[str, Tuple[str, ...]]  # director category key → (持股, 設質股數, 設質比例) as published
    note: str                    # 備註 (stripped; "" when none)
    reason: str                  # 未設置經理人之理由 and the like


@dataclass(frozen=True)
class InsiderChange:
    identity: str                # 身份別 ("董事長本人之配偶及未成年子女")
    name: str                    # 姓名; "" on the 配偶及未成年子女 rows
    share_type: str              # 持股種類 ("普通股")
    last_month: Optional[int]    # 上月實際持有股數
    this_month: Optional[int]    # 本月實際自有持有股數
    pledged: Optional[int]       # 截至本月底累計設質
    moves: Tuple[Tuple[str, Optional[int]], ...]  # (本月增加 / 本月減少 title, shares), in the reply's order

    @property
    def changed(self) -> bool:
        return any(shares for _, shares in self.moves)


@dataclass(frozen=True)
class InsiderChanges:
    name: str                    # companyAbbreviation
    year: str                    # ROC year as published ("099", "115")
    month: str                   # "01"
    changes: List[InsiderChange]


def period_body(code: str, roc_year: Optional[int] = None, month: Optional[int] = None) -> Dict[str, str]:
    """The request body for the latest month (no ``roc_year``) or ``roc_year``-``month``."""
    if roc_year is None or month is None:
        return {"companyId": code, "dataType": "1", "year": "", "month": "", "subsidiaryCompanyId": ""}
    return {"companyId": code, "dataType": "2", "year": str(roc_year), "month": f"{month:02d}", "subsidiaryCompanyId": ""}


def _rows(table: Dict[str, Any], source: str) -> Tuple[List[str], List[List[Any]]]:
    names = flatten_titles(table.get("titles") or [])
    rows = table.get("data") or []
    for r in rows:
        if not isinstance(r, list) or len(r) != len(names):
            raise UpstreamFormatError(f"{source} 資料列與 titles 對不上（{len(names)} 欄）：{str(r)[:200]}")
    return names, rows


def board_holdings(client: TWSEAPIClient, code: str, roc_year: Optional[int] = None,
                   month: Optional[int] = None) -> Optional[BoardHoldings]:
    """``code``'s directors' and officers' holdings (stapap1) for the latest month or ``roc_year``-``month``, or None
    when MOPS has none. Raises ``UpstreamFormatError`` if the titles changed."""
    result = mops_post(client, "stapap1", period_body(code, roc_year, month))
    parent = (result or {}).get("parentCompany") or {}
    if not parent.get("data"):
        return None
    names, rows = _rows(parent, "stapap1")
    col = column_index(names, ("職稱", "姓名"), "stapap1")
    others = [i for i, n in enumerate(names) if i not in (col["職稱"], col["姓名"])]
    totals = parent.get("total") or {}
    return BoardHoldings(
        name=str(parent.get("companyAbbreviation") or "").strip(),
        yymm=str(parent.get("yymm") or ""),
        columns=tuple(names[i] for i in others),
        holdings=[BoardHolding(title=str(r[col["職稱"]]), name=str(r[col["姓名"]]),
                               values=tuple(str(r[i]) for i in others)) for r in rows],
        totals={str(k): tuple(str(v) for v in values) for k, values in totals.items()},
        note=str(parent.get("note") or "").strip(),
        reason=str(parent.get("reason") or "").strip(),
    )


def insider_changes(client: TWSEAPIClient, code: str, roc_year: Optional[int] = None,
                    month: Optional[int] = None) -> Optional[InsiderChanges]:
    """``code``'s insiders' monthly holding changes (query6_1) for the latest month or ``roc_year``-``month``, or None
    when MOPS has none. Raises ``UpstreamFormatError`` if the titles changed."""
    result = mops_post(client, "query6_1", period_body(code, roc_year, month))
    if not result or not result.get("data"):
        return None
    names, rows = _rows(result, "query6_1")
    col = column_index(names, ("身份別", "姓名", "持股種類", "上月實際持有股數", "本月實際自有持有股數", "截至本月底累計設質"),
                       "query6_1")
    moves = [i for i, n in enumerate(names) if n.split(" ", 1)[0] in CHANGE_GROUPS]
    if not moves:
        raise UpstreamFormatError(f"query6_1 找不到「本月增加」「本月減少」欄位：{names}")
    return InsiderChanges(
        name=str(result.get("companyAbbreviation") or "").strip(),
        year=str(result.get("year") or ""),
        month=str(result.get("month") or ""),
        changes=[InsiderChange(
            identity=str(r[col["身份別"]]).strip(),
            name=str(r[col["姓名"]]).strip(),
            share_type=str(r[col["持股種類"]]).strip(),
            last_month=int_or_none(r[col["上月實際持有股數"]]),
            this_month=int_or_none(r[col["本月實際自有持有股數"]]),
            pledged=int_or_none(r[col["截至本月底累計設質"]]),
            moves=tuple((names[i], int_or_none(r[i])) for i in moves),
        ) for r in rows],
    )
