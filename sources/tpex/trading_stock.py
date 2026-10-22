"""TPEx afterTrading/tradingStock: one OTC security's daily trading for one calendar month.

``GET https://www.tpex.org.tw/www/zh-tw/afterTrading/tradingStock?code=6488&date=2026/10/01&response=json``
(any day of the month). Reply::

    {"stat": "ok", "date": "20261001", "code": "6488", "name": "環球晶",
     "tables": [{"title": "個股日成交資訊", "subtitle": "6488 環球晶 115年10月",
                 "fields": ["日 期", "成交張數", "成交仟元", "開盤", "最高", "最低", "收盤", "漲跌", "筆數"],
                 "data": [["115/10/01", "24,330", "26,580,157", "1,055.00", "1,135.00", "1,045.00",
                           "1,085.00", "50.00", "39,220"], ...]}]}

A code TPEx does not trade (a listed stock, a typo) or a month without trades answers ``stat``
"ok" with an empty table. Unlike TWSE's STOCK_DAY (sources/twse/stock_day.py), volume is in
thousands of shares and value in NT$ thousands, and 漲跌 has no "+" sign. The volume column is
成交張數 from 2025-01 and 成交仟股 in every earlier month (checked back to 2005): the same number,
1 張 being 1,000 shares.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import List, Optional

from utils.api_client import TWSEAPIClient
from utils.date_helper import parse_roc_date, slash_date
from utils.errors import UpstreamFormatError
from utils.parse import decimal_or_none, int_or_none

from ..caching import month_cache_ttl
from ..columns import column_index

TRADING_STOCK_URL = "https://www.tpex.org.tw/www/zh-tw/afterTrading/tradingStock"
SOURCE = "afterTrading/tradingStock"
# Published as "日 期"; names are compared without spaces so that one does not matter.
FIELDS = ("日期", "成交仟元", "開盤", "最高", "最低", "收盤", "漲跌", "筆數")
VOLUME_FIELDS = ("成交張數", "成交仟股")  # from 2025-01 / before


@dataclass(frozen=True)
class TradingStockRow:
    day: date
    lots: Optional[int]             # 成交張數 / 成交仟股 (1 張 = 1,000 shares)
    value_thousands: Optional[int]  # 成交仟元 (NT$ thousand)
    open: Optional[Decimal]         # Decimal keeps the printed digits ("1085.00"); None on "--"
    high: Optional[Decimal]
    low: Optional[Decimal]
    close: Optional[Decimal]
    change: str                     # 漲跌 exactly as published: "50.00", "-0.50", "0.00"
    transactions: Optional[int]     # 筆數


@dataclass(frozen=True)
class TradingStockMonth:
    code: str
    name: str                       # "" if TPEx gives none
    rows: List[TradingStockRow]


def trading_stock_month(client: TWSEAPIClient, code: str, year: int, month: int) -> Optional[TradingStockMonth]:
    """``code``'s trading days in ``year``-``month``, or None when TPEx has none (not an OTC code,
    or no trades that month). Raises ``UpstreamFormatError`` if the reply's shape or columns changed."""
    resp = client.fetch_json(
        TRADING_STOCK_URL,
        params={"code": code, "date": slash_date(f"{year}{month:02d}01"), "response": "json"},
        cache_ttl=month_cache_ttl(year, month),
    )
    tables = resp.get("tables") if isinstance(resp, dict) else None
    if not isinstance(resp, dict) or not isinstance(tables, list):
        raise UpstreamFormatError(f"{SOURCE} 回應不再有 tables：{str(resp)[:120]}")
    table = tables[0] if tables and isinstance(tables[0], dict) else {}
    data = table.get("data") or []
    if not data:
        return None
    fields = ["".join(str(f).split()) for f in table.get("fields") or []]
    volume = next((name for name in VOLUME_FIELDS if name in fields), VOLUME_FIELDS[0])
    col = column_index(fields, FIELDS + (volume,), SOURCE)
    rows = []
    for r in data:
        if len(r) != len(fields):
            raise UpstreamFormatError(f"{SOURCE} 資料列有 {len(r)} 欄，欄位有 {len(fields)} 個：{r}")
        day = parse_roc_date(r[col["日期"]])
        if day is None:
            raise UpstreamFormatError(f"{SOURCE} 日期格式已變更：{r[col['日期']]!r}")
        rows.append(TradingStockRow(
            day=day,
            lots=int_or_none(r[col[volume]]),
            value_thousands=int_or_none(r[col["成交仟元"]]),
            open=decimal_or_none(r[col["開盤"]]),
            high=decimal_or_none(r[col["最高"]]),
            low=decimal_or_none(r[col["最低"]]),
            close=decimal_or_none(r[col["收盤"]]),
            change=str(r[col["漲跌"]]),
            transactions=int_or_none(r[col["筆數"]]),
        ))
    return TradingStockMonth(code=code, name=str(resp.get("name") or ""), rows=rows)
