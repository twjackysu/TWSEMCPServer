"""pcRatioDown: 臺指選擇權 Put/Call Ratio — each trading day's put/call volume and open interest.

``POST https://www.taifex.com.tw/cht/3/pcRatioDown`` with the date range (30 days at most). Reply (cp950 CSV,
rows one empty cell wider than the header)::

    日期,賣權成交量,買權成交量,買賣權成交量比率%,賣權未平倉量,買權未平倉量,買賣權未平倉量比率%
    2021/01/04,409683,362995,112.86,291020,209950,138.61,

Columns are found by name; same layout checked 2005–2026.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import List, Optional

from utils.api_client import TWSEAPIClient
from utils.taifex import TAIFEX_DOWNLOAD_BASE

from .download import count, download_table, number, trade_date

PC_RATIO_DOWN_URL = f"{TAIFEX_DOWNLOAD_BASE}/pcRatioDown"
FIELDS = ("日期", "賣權成交量", "買權成交量", "買賣權成交量比率%", "賣權未平倉量", "買權未平倉量", "買賣權未平倉量比率%")


@dataclass(frozen=True)
class PutCallRatioDay:
    day: date
    put_volume: Optional[int]       # 賣權成交量 (contracts)
    call_volume: Optional[int]
    volume_ratio: Optional[Decimal]  # 買賣權成交量比率%, as published ("101.07")
    put_oi: Optional[int]           # 賣權未平倉量
    call_oi: Optional[int]
    oi_ratio: Optional[Decimal]      # 買賣權未平倉量比率%


def put_call_ratios(client: TWSEAPIClient, start: date, end: date) -> Optional[List[PutCallRatioDay]]:
    """Every trading day's Put/Call Ratio from ``start`` to ``end`` in TAIFEX's order, or None when it has none
    (including a range it rejects)."""
    table = download_table(client, PC_RATIO_DOWN_URL, "pcRatioDown", FIELDS, start, end)
    if table is None:
        return None
    col, rows = table
    return [PutCallRatioDay(
        day=trade_date(r[col["日期"]], "pcRatioDown"),
        put_volume=count(r[col["賣權成交量"]]),
        call_volume=count(r[col["買權成交量"]]),
        volume_ratio=number(r[col["買賣權成交量比率%"]]),
        put_oi=count(r[col["賣權未平倉量"]]),
        call_oi=count(r[col["買權未平倉量"]]),
        oi_ratio=number(r[col["買賣權未平倉量比率%"]]),
    ) for r in rows]
