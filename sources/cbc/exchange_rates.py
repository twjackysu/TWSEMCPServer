"""中央銀行 DataAPI BP01D01: 我國與主要貿易對手通貨對美元之匯率 — daily rates since 1993.

``GET https://cpx.cbc.gov.tw/API/DataAPI/Get?FileName=BP01D01`` returns the whole file as JSON (~1.3 MB)::

    {"meta": {"title": "我國與主要貿易對手通貨對美元之匯率依期間", "last_updated": "2026-10-01", …},
     "data": {"structure": {"Table1": [{"data": "新台幣NTD/USD"}, {"data": "日圓JPY/USD"}, …]},
              "dataSets": [["19930105", "25.405", "125.25", …], …, ["20260930", "31.852", "156.89", …]]}}

Each row is the date (YYYYMMDD) and one rate per Table1 currency, oldest day first, all strings with the published
decimals ("2048.0", "1.6560"), "-" where the file has no rate (歐元 in 1993, 馬克 in 2026). Table1 names carry stray
spaces (" 菲律賓披索PHP/USD") and say the direction: NTD/USD is NT$ per US$, USD/EUR US$ per euro. The rates are
each day's 16:00 inter-bank spot rate. CBC refreshes the file about monthly, so the latest weeks may be missing.
"""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional, Tuple

from utils.api_client import TWSEAPIClient
from utils.errors import UpstreamFormatError
from utils.parse import decimal_or_none

URL = "https://cpx.cbc.gov.tw/API/DataAPI/Get"
FILE = "BP01D01"
# The whole 1993-to-date file comes back on every request and CBC refreshes it about monthly.
CACHE_TTL = 3600
SOURCE = "央行匯率 BP01D01"


@dataclass(frozen=True)
class RateDay:
    date: date
    rates: Tuple[Optional[Decimal], ...]  # one per RateTable.currencies; None where the file has "-"


@dataclass(frozen=True)
class RateTable:
    currencies: Tuple[str, ...]  # Table1 names without stray spaces ("新台幣NTD/USD", "歐元USD/EUR")
    days: List[RateDay]          # oldest first
    last_updated: str            # meta.last_updated as published ("2026-10-01"); "" without one


def _rate(cell) -> Optional[Decimal]:
    if cell == "-":
        return None
    value = decimal_or_none(cell)
    if value is None:
        raise UpstreamFormatError(f"{SOURCE} 匯率格式已變更：{cell!r}")
    return value


def exchange_rates(client: TWSEAPIClient) -> Optional[RateTable]:
    """The whole BP01D01 file, or None when it has no currencies or no days. Raises ``UpstreamFormatError`` if the
    JSON's shape changed."""
    resp = client.fetch_json(URL, params={"FileName": FILE}, timeout=60, cache_ttl=CACHE_TTL)
    data = resp.get("data") if isinstance(resp, dict) else None
    table1 = (data.get("structure") or {}).get("Table1") if isinstance(data, dict) else None
    rows = data.get("dataSets") if isinstance(data, dict) else None
    if not isinstance(table1, list) or not isinstance(rows, list):
        raise UpstreamFormatError(f"{SOURCE} 回應結構已變更（找不到 data.structure.Table1／data.dataSets）")
    if not table1 or not rows:
        return None
    currencies = tuple(str(c.get("data", "")).strip() for c in table1)
    days = []
    for r in rows:
        if not isinstance(r, list) or len(r) != len(currencies) + 1:
            raise UpstreamFormatError(f"{SOURCE} 資料列與 Table1（{len(currencies)} 種幣別）對不上：{str(r)[:200]}")
        try:
            day = datetime.strptime(str(r[0]), "%Y%m%d").date()
        except ValueError:
            raise UpstreamFormatError(f"{SOURCE} 日期格式已變更：{r[0]!r}") from None
        days.append(RateDay(date=day, rates=tuple(_rate(c) for c in r[1:])))
    meta = resp.get("meta") or {}
    return RateTable(currencies=currencies, days=days, last_updated=str(meta.get("last_updated") or ""))
