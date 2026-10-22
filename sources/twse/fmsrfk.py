"""FMSRFK: 個股月成交資訊 — one listed security's trading summed per month, for one calendar year.

``GET https://www.twse.com.tw/rwd/zh/afterTrading/FMSRFK?response=json&stockNo=2330&date=20250103`` (any day of the
year; no ``date`` = this year, months so far). Reply::

    {"stat": "OK", "date": "20250103", "title": "114年2330 台積電           月成交資訊",
     "fields": ["年度", "月份", "最高價", "最低價", "加權(A/B)平均價", "成交筆數", "成交金額(A)", "成交股數(B)", "週轉率(%)"],
     "data": [[114, 1, "1,160.00", "1,055.00", "1,105.45", "919,543", "726,797,248,009", "657,463,196", "2.53"], ...]}

年度 (ROC) and 月份 are JSON numbers, the rest strings with thousands separators. A code TWSE does not list answers
another ``stat``. Same layout checked 2005–2026.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import List, Optional

from utils.api_client import TWSEAPIClient
from utils.date_helper import taipei_today
from utils.errors import UpstreamFormatError
from utils.parse import decimal_or_none, int_or_none

from ..caching import year_cache_ttl
from ..columns import column_index

FMSRFK_URL = "https://www.twse.com.tw/rwd/zh/afterTrading/FMSRFK"
SOURCE = "FMSRFK"
FIELDS = ("年度", "月份", "最高價", "最低價", "加權(A/B)平均價", "成交筆數", "成交金額(A)", "成交股數(B)", "週轉率(%)")


@dataclass(frozen=True)
class MonthlyTrading:
    year: int                      # 年度 (ROC)
    month: int                     # 月份
    high: Optional[Decimal]        # 最高價
    low: Optional[Decimal]         # 最低價
    average: Optional[Decimal]     # 加權(A/B)平均價 = 成交金額 / 成交股數
    transactions: Optional[int]    # 成交筆數
    value: Optional[int]           # 成交金額(A) (元)
    volume: Optional[int]          # 成交股數(B)
    turnover: Optional[Decimal]    # 週轉率(%)


@dataclass(frozen=True)
class MonthlyTradingYear:
    title: str                     # "114年2330 台積電           月成交資訊"
    months: List[MonthlyTrading]


def monthly_trading(client: TWSEAPIClient, code: str, date: str = "") -> Optional[MonthlyTradingYear]:
    """``code``'s monthly trading in the year of ``date`` (YYYYMMDD; "" = this year), or None when TWSE has none
    (not a listed code). Raises ``UpstreamFormatError`` if the reply changed."""
    params = {"response": "json", "stockNo": code}
    if date:
        params["date"] = date
    year = int(date[:4]) if date else taipei_today().year
    resp = client.fetch_json(FMSRFK_URL, params=params, cache_ttl=year_cache_ttl(year))
    if not isinstance(resp, dict):
        raise UpstreamFormatError(f"{SOURCE} 回應不是 JSON 物件：{str(resp)[:120]}")
    if resp.get("stat") != "OK":
        return None
    title = str(resp.get("title") or "")
    data = resp.get("data") or []
    if not data:
        return MonthlyTradingYear(title=title, months=[])
    fields = [str(f).strip() for f in resp.get("fields") or []]
    col = column_index(fields, FIELDS, SOURCE)
    months = []
    for r in data:
        if len(r) != len(fields):
            raise UpstreamFormatError(f"{SOURCE} 資料列有 {len(r)} 欄，欄位有 {len(fields)} 個：{r}")
        roc_year, month = int_or_none(r[col["年度"]]), int_or_none(r[col["月份"]])
        if roc_year is None or month is None:
            raise UpstreamFormatError(f"{SOURCE} 年度／月份格式已變更：{r}")
        months.append(MonthlyTrading(
            year=roc_year,
            month=month,
            high=decimal_or_none(r[col["最高價"]]),
            low=decimal_or_none(r[col["最低價"]]),
            average=decimal_or_none(r[col["加權(A/B)平均價"]]),
            transactions=int_or_none(r[col["成交筆數"]]),
            value=int_or_none(r[col["成交金額(A)"]]),
            volume=int_or_none(r[col["成交股數(B)"]]),
            turnover=decimal_or_none(r[col["週轉率(%)"]]),
        ))
    return MonthlyTradingYear(title=title, months=months)
