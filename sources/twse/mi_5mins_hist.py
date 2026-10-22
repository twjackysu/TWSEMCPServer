"""MI_5MINS_HIST: 發行量加權股價指數歷史資料 — TAIEX daily open, high, low and close for one calendar month.

``GET https://www.twse.com.tw/rwd/zh/TAIEX/MI_5MINS_HIST?response=json&date=20250103`` (any day of the month; no
``date`` = this month). Reply::

    {"stat": "OK", "date": "20250103", "title": "114年01月 發行量加權股價指數歷史資料",
     "fields": ["日期", "開盤指數", "最高指數", "最低指數", "收盤指數"],
     "data": [["114/01/02", "22,975.71", "23,038.08", "22,713.63", "22,832.06"], ...]}

Dates before ROC 100 are padded (" 94/01/03"). Same layout checked 2005–2026.
"""

from dataclasses import dataclass
from datetime import date as Date
from decimal import Decimal
from typing import List, Optional

from utils.api_client import TWSEAPIClient
from utils.date_helper import parse_roc_date, taipei_today
from utils.errors import UpstreamFormatError
from utils.parse import decimal_or_none

from ..caching import month_cache_ttl
from ..columns import column_index

MI_5MINS_HIST_URL = "https://www.twse.com.tw/rwd/zh/TAIEX/MI_5MINS_HIST"
SOURCE = "MI_5MINS_HIST"
FIELDS = ("日期", "開盤指數", "最高指數", "最低指數", "收盤指數")


@dataclass(frozen=True)
class IndexDay:
    day: Date
    open: Optional[Decimal]
    high: Optional[Decimal]
    low: Optional[Decimal]
    close: Optional[Decimal]


@dataclass(frozen=True)
class IndexMonth:
    date: str                    # YYYYMMDD TWSE served
    title: str                   # "114年01月 發行量加權股價指數歷史資料"
    days: List[IndexDay]


def taiex_history(client: TWSEAPIClient, date: str = "") -> Optional[IndexMonth]:
    """TAIEX OHLC for every trading day of the month of ``date`` (YYYYMMDD; "" = this month), or None when TWSE
    answers with anything but OK. Raises ``UpstreamFormatError`` if the reply changed."""
    params = {"response": "json"}
    if date:
        params["date"] = date
    month = (int(date[:4]), int(date[4:6])) if date else (taipei_today().year, taipei_today().month)
    resp = client.fetch_json(MI_5MINS_HIST_URL, params=params, cache_ttl=month_cache_ttl(*month))
    if not isinstance(resp, dict):
        raise UpstreamFormatError(f"{SOURCE} 回應不是 JSON 物件：{str(resp)[:120]}")
    if resp.get("stat") != "OK":
        return None
    served, title = str(resp.get("date") or date), str(resp.get("title") or "")
    data = resp.get("data") or []
    if not data:
        return IndexMonth(date=served, title=title, days=[])
    fields = [str(f).strip() for f in resp.get("fields") or []]
    col = column_index(fields, FIELDS, SOURCE)
    days = []
    for r in data:
        if len(r) != len(fields):
            raise UpstreamFormatError(f"{SOURCE} 資料列有 {len(r)} 欄，欄位有 {len(fields)} 個：{r}")
        day = parse_roc_date(r[col["日期"]])
        if day is None:
            raise UpstreamFormatError(f"{SOURCE} 日期格式已變更：{r[col['日期']]!r}")
        days.append(IndexDay(
            day=day,
            open=decimal_or_none(r[col["開盤指數"]]),
            high=decimal_or_none(r[col["最高指數"]]),
            low=decimal_or_none(r[col["最低指數"]]),
            close=decimal_or_none(r[col["收盤指數"]]),
        ))
    return IndexMonth(date=served, title=title, days=days)
