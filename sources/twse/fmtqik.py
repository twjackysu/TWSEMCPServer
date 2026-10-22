"""FMTQIK: 市場成交資訊 — the listed market's daily turnover and TAIEX close, for one calendar month.

``GET https://www.twse.com.tw/rwd/zh/afterTrading/FMTQIK?response=json&date=20250103`` (any day of the month; no
``date`` = this month). Reply::

    {"stat": "OK", "date": "20250103", "title": "114年01月市場成交資訊",
     "fields": ["日期", "成交股數", "成交金額", "成交筆數", "發行量加權股價指數", "漲跌點數"],
     "data": [["114/01/02", "6,901,476,303", "379,129,283,886", "2,742,811", "22,832.06", "-203.04"], ...]}

Dates before ROC 100 are padded (" 94/01/03"). Same layout checked 2005–2026.
"""

from dataclasses import dataclass
from datetime import date as Date
from decimal import Decimal
from typing import List, Optional

from utils.api_client import TWSEAPIClient
from utils.date_helper import parse_roc_date, taipei_today
from utils.errors import UpstreamFormatError
from utils.parse import decimal_or_none, int_or_none

from ..caching import month_cache_ttl
from ..columns import column_index

FMTQIK_URL = "https://www.twse.com.tw/rwd/zh/afterTrading/FMTQIK"
SOURCE = "FMTQIK"
FIELDS = ("日期", "成交股數", "成交金額", "成交筆數", "發行量加權股價指數", "漲跌點數")


@dataclass(frozen=True)
class MarketDay:
    day: Date
    volume: Optional[int]        # 成交股數
    value: Optional[int]         # 成交金額 (元)
    transactions: Optional[int]  # 成交筆數
    index: Optional[Decimal]     # 發行量加權股價指數 (close)
    change: Optional[Decimal]    # 漲跌點數, signed ("-203.04")


@dataclass(frozen=True)
class MarketMonth:
    date: str                    # YYYYMMDD TWSE served
    title: str                   # "114年01月市場成交資訊"
    days: List[MarketDay]


def market_turnover(client: TWSEAPIClient, date: str = "") -> Optional[MarketMonth]:
    """Every trading day of the month of ``date`` (YYYYMMDD; "" = this month), or None when TWSE answers with
    anything but OK. Raises ``UpstreamFormatError`` if the reply changed."""
    params = {"response": "json"}
    if date:
        params["date"] = date
    month = (int(date[:4]), int(date[4:6])) if date else (taipei_today().year, taipei_today().month)
    resp = client.fetch_json(FMTQIK_URL, params=params, cache_ttl=month_cache_ttl(*month))
    if not isinstance(resp, dict):
        raise UpstreamFormatError(f"{SOURCE} 回應不是 JSON 物件：{str(resp)[:120]}")
    if resp.get("stat") != "OK":
        return None
    served, title = str(resp.get("date") or date), str(resp.get("title") or "")
    data = resp.get("data") or []
    if not data:
        return MarketMonth(date=served, title=title, days=[])
    fields = [str(f).strip() for f in resp.get("fields") or []]
    col = column_index(fields, FIELDS, SOURCE)
    days = []
    for r in data:
        if len(r) != len(fields):
            raise UpstreamFormatError(f"{SOURCE} 資料列有 {len(r)} 欄，欄位有 {len(fields)} 個：{r}")
        day = parse_roc_date(r[col["日期"]])
        if day is None:
            raise UpstreamFormatError(f"{SOURCE} 日期格式已變更：{r[col['日期']]!r}")
        days.append(MarketDay(
            day=day,
            volume=int_or_none(r[col["成交股數"]]),
            value=int_or_none(r[col["成交金額"]]),
            transactions=int_or_none(r[col["成交筆數"]]),
            index=decimal_or_none(r[col["發行量加權股價指數"]]),
            change=decimal_or_none(r[col["漲跌點數"]]),
        ))
    return MarketMonth(date=served, title=title, days=days)
