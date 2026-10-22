"""STOCK_DAY_AVG: 日收盤價及月平均收盤價 — one listed security's closes for one calendar month and their average.

``GET https://www.twse.com.tw/exchangeReport/STOCK_DAY_AVG?response=json&stockNo=2330&date=20250103`` (any day of
the month; no ``date`` = this month). Reply::

    {"stat": "OK", "date": "20250103", "title": "114年01月 2330 台積電 日收盤價及月平均收盤價",
     "fields": ["日期", "收盤價"],
     "data": [["114/01/02", "1,065.00"], ..., ["114/01/22", "1,135.00"], ["月平均收盤價", "1102.00"]]}

The last row is the month's average, labelled in the 日期 column and printed without thousands separators
("1102.00") where the closes have them. Dates before ROC 100 are padded (" 94/01/03"). A code TWSE does not list,
or a month without trades, answers with another ``stat`` and nothing else. Same layout checked 2005–2026.
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

STOCK_DAY_AVG_URL = "https://www.twse.com.tw/exchangeReport/STOCK_DAY_AVG"
SOURCE = "STOCK_DAY_AVG"
FIELDS = ("日期", "收盤價")
AVERAGE_LABEL = "月平均收盤價"


@dataclass(frozen=True)
class DailyClose:
    day: Date
    close: Optional[Decimal]     # 收盤價 as published ("1,065.00" → 1065.00); None on "--"


@dataclass(frozen=True)
class MonthlyCloses:
    date: str                    # YYYYMMDD TWSE served
    title: str                   # "114年01月 2330 台積電 日收盤價及月平均收盤價"
    closes: List[DailyClose]
    average: Optional[Decimal]   # 月平均收盤價, printed by TWSE without thousands separators


def monthly_closes(client: TWSEAPIClient, code: str, date: str = "") -> Optional[MonthlyCloses]:
    """``code``'s closes in the month of ``date`` (YYYYMMDD; "" = this month) and their average, or None when
    TWSE has none (not a listed code, no trades that month). Raises ``UpstreamFormatError`` if the reply changed."""
    params = {"response": "json", "stockNo": code}
    if date:
        params["date"] = date
    month = (int(date[:4]), int(date[4:6])) if date else (taipei_today().year, taipei_today().month)
    resp = client.fetch_json(STOCK_DAY_AVG_URL, params=params, cache_ttl=month_cache_ttl(*month))
    if not isinstance(resp, dict):
        raise UpstreamFormatError(f"{SOURCE} 回應不是 JSON 物件：{str(resp)[:120]}")
    if resp.get("stat") != "OK":
        return None
    served, title = str(resp.get("date") or date), str(resp.get("title") or "")
    data = resp.get("data") or []
    if not data:
        return MonthlyCloses(date=served, title=title, closes=[], average=None)
    fields = [str(f).strip() for f in resp.get("fields") or []]
    col = column_index(fields, FIELDS, SOURCE)
    closes, average = [], None
    for r in data:
        if len(r) != len(fields):
            raise UpstreamFormatError(f"{SOURCE} 資料列有 {len(r)} 欄，欄位有 {len(fields)} 個：{r}")
        label = str(r[col["日期"]]).strip()
        if label == AVERAGE_LABEL:
            average = decimal_or_none(r[col["收盤價"]])
            continue
        day = parse_roc_date(label)
        if day is None:
            raise UpstreamFormatError(f"{SOURCE} 日期欄出現不認得的值：{label!r}")
        closes.append(DailyClose(day=day, close=decimal_or_none(r[col["收盤價"]])))
    return MonthlyCloses(date=served, title=title, closes=closes, average=average)
