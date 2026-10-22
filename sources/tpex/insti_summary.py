"""TPEx insti/summary: 三大法人買賣金額彙總表 — the OTC market's institutional buy / sell amounts for a day, a
week or a month, in NT$.

``GET https://www.tpex.org.tw/www/zh-tw/insti/summary?type=Daily&prod=1&date=2025/01/03&response=json``
(``type`` Daily / Weekly / Monthly with any day of that week or month; no ``date`` = latest; ``prod`` 1 上櫃股票,
0 上櫃有價證券). Reply::

    {"date": "20250103", "stat": "ok",
     "tables": [{"subtitle": "114年01月03日上櫃股票三大法人日彙總交易資訊",
                 "fields": ["單位名稱", "買進金額(元)", "賣出金額(元)", "買賣超(元)"],
                 "data": [["外資及陸資合計", "20,309,758,499", "17,880,081,999", "2,429,676,500"],
                          ["　外資及陸資(不含自營商)", ...], ["　外資自營商", ...], ["投信", ...],
                          ["自營商合計", ...], ["　自營商(自行買賣)", ...], ["　自營商(避險)", ...],
                          ["三大法人合計*", ...]]}]}

Sub-items are indented with an ideographic space, stripped here. Some days carry an empty row ``[]`` (on
2018-01-02 after the four rows TPEx had for that day), which is skipped; reading it by position failed.
A period without data is an empty table.
"""

from dataclasses import dataclass
from typing import List

from utils.api_client import TWSEAPIClient
from utils.date_helper import slash_date
from utils.errors import UpstreamFormatError
from utils.parse import int_or_none

from ..caching import day_cache_ttl
from ..columns import column_index
from ..institutional import InstitutionalAmount

INSTI_SUMMARY_URL = "https://www.tpex.org.tw/www/zh-tw/insti/summary"
SOURCE = "insti/summary"
FIELDS = ("單位名稱", "買進金額(元)", "賣出金額(元)", "買賣超(元)")
STOCKS, ALL_SECURITIES = "1", "0"  # prod


@dataclass(frozen=True)
class InstitutionalSummary:
    date: str             # the day TPEx answered for, YYYYMMDD
    subtitle: str         # "114年01月03日上櫃股票三大法人日彙總交易資訊"; "" for a period without data
    amounts: List[InstitutionalAmount]  # empty for a period without data


def otc_institutional_amounts(client: TWSEAPIClient, period: str = "Daily", prod: str = STOCKS,
                              date: str = "") -> InstitutionalSummary:
    """The OTC market's 三大法人 amounts for the ``period`` (Daily, Weekly or Monthly) containing ``date``
    (YYYYMMDD; "" = latest). Raises ``UpstreamFormatError`` if the reply's shape or columns changed."""
    params = {"type": period, "prod": prod}
    if date:
        params["date"] = slash_date(date)
    resp = client.fetch_json(INSTI_SUMMARY_URL, params={**params, "response": "json"}, cache_ttl=day_cache_ttl(date))
    tables = resp.get("tables") if isinstance(resp, dict) else None
    if not isinstance(resp, dict) or not isinstance(tables, list):
        raise UpstreamFormatError(f"{SOURCE} 回應不再有 tables：{str(resp)[:120]}")
    table = tables[0] if tables and isinstance(tables[0], dict) else {}
    served, subtitle = str(resp.get("date") or ""), str(table.get("subtitle") or "")
    data = [r for r in table.get("data") or [] if r]  # some days carry an empty row
    if not data:
        return InstitutionalSummary(date=served, subtitle=subtitle, amounts=[])
    fields = [str(f).strip() for f in table.get("fields") or []]
    col = column_index(fields, FIELDS, SOURCE)
    amounts = []
    for r in data:
        if len(r) != len(fields):
            raise UpstreamFormatError(f"{SOURCE} 資料列有 {len(r)} 欄，欄位有 {len(fields)} 個：{r}")
        amounts.append(InstitutionalAmount(
            name=str(r[col["單位名稱"]]).strip(),
            buy=int_or_none(r[col["買進金額(元)"]]),
            sell=int_or_none(r[col["賣出金額(元)"]]),
            net=int_or_none(r[col["買賣超(元)"]]),
        ))
    return InstitutionalSummary(date=served, subtitle=subtitle, amounts=amounts)
