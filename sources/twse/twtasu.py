"""TWTASU: 當日融券賣出與借券賣出成交量值 — each listed security's short sales and securities-lending sales on one day.

``GET https://www.twse.com.tw/rwd/zh/afterTrading/TWTASU?response=json&date=20250103`` (from 2008-09-26; earlier
dates answer ``stat`` 查詢日期小於97年9月26日). Reply::

    {"stat": "OK", "date": "20250103", "title": "114年01月03日當日融券賣出與借券賣出成交量值",
     "groups": [{"start": 0, "span": 1, "title": ""}, {"start": 1, "span": 2, "title": "融券賣出成交"},
                {"start": 3, "span": 2, "title": "借券賣出成交"}],
     "fields": ["證券名稱", "數量", "金額", "數量", "金額"],
     "data": [["0050   元大台灣50      ", "11", "2,155,050", "0", "0"], ..., ["合計", "21,933", "1,992,535,570", ...]]}

Both groups have a 數量 and a 金額, so a column is found by group and name ("借券賣出成交/數量"). 證券名稱 holds the code
and the name, padded with spaces; the closing 合計 row is left out. Same layout checked 2008–2026.
"""

from dataclasses import dataclass
from typing import List, Optional

from utils.api_client import TWSEAPIClient
from utils.constants import SUMMARY_ROW_LABELS
from utils.errors import UpstreamFormatError
from utils.parse import int_or_none

from ..caching import day_cache_ttl
from ..columns import column_index, qualified_fields

TWTASU_URL = "https://www.twse.com.tw/rwd/zh/afterTrading/TWTASU"
SOURCE = "TWTASU"
FIELDS = ("證券名稱", "融券賣出成交/數量", "融券賣出成交/金額", "借券賣出成交/數量", "借券賣出成交/金額")


@dataclass(frozen=True)
class ShortLendingSale:
    code: str
    name: str
    short_volume: Optional[int]    # 融券賣出成交 數量
    short_value: Optional[int]     # 融券賣出成交 金額 (元)
    lending_volume: Optional[int]  # 借券賣出成交 數量
    lending_value: Optional[int]   # 借券賣出成交 金額 (元)


@dataclass(frozen=True)
class ShortLendingSaleDay:
    date: str    # YYYYMMDD
    title: str   # "114年01月03日當日融券賣出與借券賣出成交量值"
    sales: List[ShortLendingSale]  # without the 合計 row


def short_lending_sales(client: TWSEAPIClient, date: str) -> Optional[ShortLendingSaleDay]:
    """Every listed security's 融券賣出 and 借券賣出 on ``date`` (YYYYMMDD), or None when TWSE has none (not a
    trading day, before 2008-09-26). Raises ``UpstreamFormatError`` if the reply's columns changed."""
    resp = client.fetch_json(TWTASU_URL, params={"response": "json", "date": date}, cache_ttl=day_cache_ttl(date))
    if not isinstance(resp, dict):
        raise UpstreamFormatError(f"{SOURCE} 回應不是 JSON 物件：{str(resp)[:120]}")
    if resp.get("stat") != "OK":
        return None
    served, title = str(resp.get("date") or date), str(resp.get("title") or "")
    data = resp.get("data") or []
    if not data:
        return ShortLendingSaleDay(date=served, title=title, sales=[])
    names = qualified_fields(list(resp.get("fields") or []), list(resp.get("groups") or []), SOURCE)
    col = column_index(names, FIELDS, SOURCE)
    sales = []
    for r in data:
        if len(r) != len(names):
            raise UpstreamFormatError(f"{SOURCE} 資料列有 {len(r)} 欄，欄位有 {len(names)} 個：{r}")
        code_name = str(r[col["證券名稱"]]).split(None, 1)
        code = code_name[0] if code_name else ""
        if code in SUMMARY_ROW_LABELS:
            continue
        sales.append(ShortLendingSale(
            code=code,
            name=code_name[1].strip() if len(code_name) > 1 else "",
            short_volume=int_or_none(r[col["融券賣出成交/數量"]]),
            short_value=int_or_none(r[col["融券賣出成交/金額"]]),
            lending_volume=int_or_none(r[col["借券賣出成交/數量"]]),
            lending_value=int_or_none(r[col["借券賣出成交/金額"]]),
        ))
    return ShortLendingSaleDay(date=served, title=title, sales=sales)
