"""STOCK_DAY: one listed security's daily trading for one calendar month.

``GET https://www.twse.com.tw/exchangeReport/STOCK_DAY?response=json&stockNo=2330&date=20260901``
(any day of the month). Reply::

    {"stat": "OK", "title": "115年09月 2330 台積電           各日成交資訊",
     "fields": ["日期", "成交股數", "成交金額", "開盤價", "最高價", "最低價", "收盤價", "漲跌價差", "成交筆數", "註記"],
     "data": [["115/09/01", "31,855,287", "77,463,413,685", "2,395.00", "2,440.00", "2,390.00",
               "2,440.00", "+35.00", "65,271", ""], ...]}

A code TWSE does not list, or a month without trades, answers with another ``stat`` (e.g.
"很抱歉，沒有符合條件的資料!") and no data. Prices are "--" on days without a trade.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import List, Optional

from utils.api_client import TWSEAPIClient
from utils.date_helper import parse_roc_date
from utils.errors import UpstreamFormatError
from utils.parse import decimal_or_none, int_or_none

from ..caching import month_cache_ttl
from ..columns import column_index

STOCK_DAY_URL = "https://www.twse.com.tw/exchangeReport/STOCK_DAY"
FIELDS = ("日期", "成交股數", "成交金額", "開盤價", "最高價", "最低價", "收盤價", "漲跌價差", "成交筆數")


@dataclass(frozen=True)
class StockDayRow:
    day: date
    volume: Optional[int]        # 成交股數 (shares)
    value: Optional[int]         # 成交金額 (NT$)
    open: Optional[Decimal]      # Decimal keeps the printed digits ("2440.00"); None on "--"
    high: Optional[Decimal]
    low: Optional[Decimal]
    close: Optional[Decimal]
    change: str                  # 漲跌價差 exactly as published: " 0.00", "+35.00", "-15.00"
    transactions: Optional[int]  # 成交筆數


@dataclass(frozen=True)
class StockDayMonth:
    code: str
    name: str                    # from the title; "" if the title has an unexpected shape
    title: str
    rows: List[StockDayRow]


def stock_day_month(client: TWSEAPIClient, code: str, year: int, month: int) -> Optional[StockDayMonth]:
    """``code``'s trading days in ``year``-``month``, or None when TWSE has none (not a listed
    code, or no trades that month). Raises ``UpstreamFormatError`` if the columns changed."""
    resp = client.fetch_json(
        STOCK_DAY_URL,
        params={"response": "json", "stockNo": code, "date": f"{year}{month:02d}01"},
        cache_ttl=month_cache_ttl(year, month),
    )
    if not isinstance(resp, dict):
        raise UpstreamFormatError(f"STOCK_DAY 回應不是 JSON 物件：{str(resp)[:120]}")
    if resp.get("stat") != "OK" or not resp.get("data"):
        return None
    col = column_index(resp.get("fields"), FIELDS, "STOCK_DAY")
    rows = []
    for r in resp["data"]:
        day = parse_roc_date(r[col["日期"]])
        if day is None:
            raise UpstreamFormatError(f"STOCK_DAY 日期格式已變更：{r[col['日期']]!r}")
        rows.append(StockDayRow(
            day=day,
            volume=int_or_none(r[col["成交股數"]]),
            value=int_or_none(r[col["成交金額"]]),
            open=decimal_or_none(r[col["開盤價"]]),
            high=decimal_or_none(r[col["最高價"]]),
            low=decimal_or_none(r[col["最低價"]]),
            close=decimal_or_none(r[col["收盤價"]]),
            change=str(r[col["漲跌價差"]]),
            transactions=int_or_none(r[col["成交筆數"]]),
        ))
    title = str(resp.get("title", ""))
    # title: "115年09月 2330 台積電           各日成交資訊"
    parts = title.split()
    name = parts[2] if len(parts) >= 3 and parts[1] == code else ""
    return StockDayMonth(code=code, name=name, title=title, rows=rows)
