"""MOPS t05st10_ifrs: 每月營業收入 — one company's revenue report for one month (the latest, or a given one).

``POST https://mops.twse.com.tw/mops/api/t05st10_ifrs`` with ``{"companyId", "dataType": "1" (latest) or "2",
"year" (ROC), "month" ("8", not zero-padded), "subsidiaryCompanyId": ""}``. Reply::

    {"companyAbbreviation": "台積電", "yymm": "11509", "titles": [{"main": "項目"}, {"main": "營業收入淨額"}],
     "data": [["本月", "511,857,399"], ["去年同期", "330,980,920"], ["增減金額", …], ["增減百分比", "54.65"],
              ["本年累計", …], ["去年累計", …], ["增減金額", …], ["增減百分比", …],
              ["備註/營收變化原因說明", "因先進製程產品需求增加所致。"]]}

Amounts are in 仟元, percentages in %. The two 增減 pairs belong to the month and to the year to date, in that
order. Months before IFRS (checked: 2009-12, 2010-01) answer ``yymm`` only, without data. Same titles checked
2014–2026.
"""

from dataclasses import dataclass
from typing import List, Optional, Tuple

from utils.api_client import TWSEAPIClient
from utils.date_helper import parse_roc_date, roc_year_of
from utils.errors import UpstreamFormatError
from utils.mops import leaf_titles, mops_post
from utils.parse import int_or_none

from ..columns import column_index

CURRENT_MONTH_LABEL = "本月"  # the month's revenue; the tool's month-on-month change compares it across months


@dataclass(frozen=True)
class RevenueItem:
    label: str     # 項目: 本月, 去年同期, 增減金額, 增減百分比, …, 備註/營收變化原因說明
    value: str     # 營業收入淨額 as published ("511,857,399", "54.65", the 說明 text, "")


@dataclass(frozen=True)
class MonthlyRevenue:
    name: str                          # companyAbbreviation; "" when MOPS leaves it out
    period: Optional[Tuple[int, int]]  # (西元 year, month) of yymm; None without one
    items: List[RevenueItem]           # in MOPS's order; empty for a month without a report

    @property
    def current(self) -> Optional[int]:
        """本月 revenue (仟元), or None."""
        return next((int_or_none(i.value) for i in self.items if i.label == CURRENT_MONTH_LABEL), None)


def monthly_revenue(client: TWSEAPIClient, code: str, year: Optional[int] = None,
                    month: Optional[int] = None) -> Optional[MonthlyRevenue]:
    """``code``'s revenue report for ``year``-``month`` (西元), or the latest one without them; None when MOPS has
    none. Raises ``UpstreamFormatError`` if the titles changed."""
    if year is None or month is None:
        body = {"companyId": code, "dataType": "1", "year": "", "month": "", "subsidiaryCompanyId": ""}
    else:
        body = {"companyId": code, "dataType": "2", "year": str(roc_year_of(f"{year}{month:02d}01")),
                "month": str(month), "subsidiaryCompanyId": ""}
    result = mops_post(client, "t05st10_ifrs", body)
    if result is None:
        return None
    yymm = str(result.get("yymm") or "")
    day = parse_roc_date(f"{yymm[:-2]}/{yymm[-2:]}/01") if len(yymm) >= 4 else None
    items = []
    data = result.get("data") or []
    if data:
        names = leaf_titles(result.get("titles") or [])
        col = column_index(names, ("項目", "營業收入淨額"), "t05st10_ifrs")
        for r in data:
            if not isinstance(r, list) or len(r) != len(names):
                raise UpstreamFormatError(f"t05st10_ifrs 資料列與 titles 對不上（{len(names)} 欄）：{str(r)[:200]}")
            items.append(RevenueItem(label=str(r[col["項目"]]).strip(), value=str(r[col["營業收入淨額"]]).strip()))
    return MonthlyRevenue(name=str(result.get("companyAbbreviation") or "").strip(),
                          period=(day.year, day.month) if day else None, items=items)
