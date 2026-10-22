"""BFI82U: 三大法人買賣金額統計表 — the listed market's institutional buy / sell amounts for a day, a week or a month.

``GET https://www.twse.com.tw/rwd/zh/fund/BFI82U?response=json&type=day&dayDate=20250103`` (``type`` day / week /
month with ``dayDate`` / ``weekDate`` / ``monthDate``). Reply::

    {"stat": "OK", "date": "20250103", "title": "114年01月03日 三大法人買賣金額統計表",
     "fields": ["單位名稱", "買進金額", "賣出金額", "買賣差額"],
     "data": [["自營商(自行買賣)", "4,161,637,637", "4,078,689,337", "82,948,300"], ..., ["合計", ...]]}

- day: no ``dayDate`` = the latest trading day.
- week: ``weekDate`` must be the week's first trading day (the Monday, or the Tuesday when Monday is a holiday);
  any other day answers ``stat`` 很抱歉，沒有符合條件的資料!.
- month: any day of the month (the current month runs to date); without ``monthDate`` the reply is an HTML page.

Rows are labelled as TWSE published them then: 自營商 on 2014-01-02, 自營商(自行買賣) / 自營商(避險) by
2015-01-05. Same four fields checked 2005–2026.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional

from utils.api_client import TWSEAPIClient
from utils.errors import UpstreamFormatError
from utils.parse import int_or_none

from ..caching import day_cache_ttl, month_cache_ttl
from ..columns import column_index
from ..institutional import InstitutionalAmount

BFI82U_URL = "https://www.twse.com.tw/rwd/zh/fund/BFI82U"
SOURCE = "BFI82U"
FIELDS = ("單位名稱", "買進金額", "賣出金額", "買賣差額")
DATE_PARAMS = {"day": "dayDate", "week": "weekDate", "month": "monthDate"}


@dataclass(frozen=True)
class AmountReport:
    date: str      # YYYYMMDD TWSE served
    title: str     # "114年01月03日 三大法人買賣金額統計表"
    amounts: List[InstitutionalAmount]


def _cache_ttl(period: str, date: str) -> int:
    if not date:
        return day_cache_ttl("")
    if period == "month":
        return month_cache_ttl(int(date[:4]), int(date[4:6]))
    if period == "week":  # still growing until its Sunday has passed
        return day_cache_ttl(f"{datetime.strptime(date, '%Y%m%d') + timedelta(days=6):%Y%m%d}")
    return day_cache_ttl(date)


def institutional_amounts(client: TWSEAPIClient, period: str = "day", date: str = "") -> Optional[AmountReport]:
    """The listed market's 三大法人 amounts for ``period`` (day, week or month) at ``date`` (YYYYMMDD; "" = the latest
    day — always pass one for month), or None when TWSE has none for it (not a trading day, not the week's first
    trading day). Raises ``UpstreamFormatError`` if the fields changed."""
    params = {"response": "json", "type": period}
    if date:
        params[DATE_PARAMS[period]] = date
    resp = client.fetch_json(BFI82U_URL, params=params, cache_ttl=_cache_ttl(period, date))
    if not isinstance(resp, dict):
        raise UpstreamFormatError(f"{SOURCE} 回應不是 JSON 物件：{str(resp)[:120]}")
    data = resp.get("data") or []
    if resp.get("stat") != "OK" or not data:
        return None
    fields = [str(f).strip() for f in resp.get("fields") or []]
    col = column_index(fields, FIELDS, SOURCE)
    amounts = []
    for r in data:
        if len(r) != len(fields):
            raise UpstreamFormatError(f"{SOURCE} 資料列有 {len(r)} 欄，欄位有 {len(fields)} 個：{r}")
        amounts.append(InstitutionalAmount(
            name=str(r[col["單位名稱"]]).strip(),
            buy=int_or_none(r[col["買進金額"]]),
            sell=int_or_none(r[col["賣出金額"]]),
            net=int_or_none(r[col["買賣差額"]]),
        ))
    return AmountReport(date=str(resp.get("date") or date), title=str(resp.get("title") or ""), amounts=amounts)
