"""TPEx insti/qfii: 僑外資及陸資持股比例排行表 — every OTC stock's foreign shareholding on one day, ranked by ratio.

``GET https://www.tpex.org.tw/www/zh-tw/insti/qfii?date=2025/01/03&response=json`` (no ``date`` = the latest day;
2005-01-03 has no rows, 2010-01-04 has). Reply::

    {"stat": "ok", "date": "20250103", "tables": [{"title": "櫃檯買賣股票僑外資及陸資持股比例排行表",
      "fields": ["排行", "代號", "名稱", "發行股數(A)", "僑外資及陸資尚可投資股數B=A*F-C", "僑外資及陸資持有股數(C)",
                 "僑外資及陸資尚可投資比率(D=B/A)", "僑外資及陸資持股比率(E=C/A)", "法令投資上限比率(F)", "備註"],
      "data": [["1", "8455", "大拓-KY", "25,219,056", "3,059,750", "22,159,306", "12.13%", "87.86%", "100%", ""], ...]}]}

The three ratios carry a percent sign ("87.86%", "100%"); 備註 is "已達上限", "禁止投資" or empty. A day without
trading has no rows. Same fields checked 2010–2026.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import List, Optional

from utils.api_client import TWSEAPIClient
from utils.date_helper import slash_date
from utils.errors import UpstreamFormatError
from utils.parse import decimal_or_none, int_or_none

from ..caching import day_cache_ttl
from ..columns import column_index

QFII_URL = "https://www.tpex.org.tw/www/zh-tw/insti/qfii"
SOURCE = "insti/qfii"
FIELDS = ("排行", "代號", "名稱", "發行股數(A)", "僑外資及陸資尚可投資股數B=A*F-C", "僑外資及陸資持有股數(C)",
          "僑外資及陸資尚可投資比率(D=B/A)", "僑外資及陸資持股比率(E=C/A)", "法令投資上限比率(F)", "備註")


@dataclass(frozen=True)
class OtcForeignHolding:
    rank: Optional[int]               # 排行 by 持股比率
    code: str
    name: str
    issued_shares: Optional[int]      # 發行股數(A)
    available_shares: Optional[int]   # 僑外資及陸資尚可投資股數 B = A × F − C
    held_shares: Optional[int]        # 僑外資及陸資持有股數(C)
    available_pct: Optional[Decimal]  # 尚可投資比率 D = B / A (%), published "12.13%"
    held_pct: Optional[Decimal]       # 持股比率 E = C / A (%)
    limit_pct: Optional[Decimal]      # 法令投資上限比率 F (%)
    note: str                         # 備註: 已達上限, 禁止投資, ""


@dataclass(frozen=True)
class OtcForeignHoldingDay:
    date: str                         # the day TPEx answered for, YYYYMMDD
    holdings: List[OtcForeignHolding]  # in TPEx's rank order; empty on a day without trading


def _percent(value) -> Optional[Decimal]:
    """"87.86%" → Decimal("87.86")."""
    return decimal_or_none(str(value).strip().removesuffix("%"))


def otc_foreign_holdings(client: TWSEAPIClient, date: str = "") -> OtcForeignHoldingDay:
    """Every OTC stock's foreign shareholding on ``date`` (YYYYMMDD; "" = latest day). Raises
    ``UpstreamFormatError`` if the reply's shape or columns changed."""
    params = {"response": "json"}
    if date:
        params["date"] = slash_date(date)
    resp = client.fetch_json(QFII_URL, params=params, cache_ttl=day_cache_ttl(date))
    tables = resp.get("tables") if isinstance(resp, dict) else None
    if not isinstance(resp, dict) or not isinstance(tables, list):
        raise UpstreamFormatError(f"{SOURCE} 回應不再有 tables：{str(resp)[:120]}")
    served = str(resp.get("date") or "")
    table = tables[0] if tables and isinstance(tables[0], dict) else {}
    data = table.get("data") or []
    if not data:
        return OtcForeignHoldingDay(date=served, holdings=[])
    fields = [str(f).strip() for f in table.get("fields") or []]
    col = column_index(fields, FIELDS, SOURCE)
    holdings = []
    for r in data:
        if len(r) != len(fields):
            raise UpstreamFormatError(f"{SOURCE} 資料列有 {len(r)} 欄，欄位有 {len(fields)} 個：{r}")
        holdings.append(OtcForeignHolding(
            rank=int_or_none(r[col["排行"]]),
            code=str(r[col["代號"]]).strip(),
            name=str(r[col["名稱"]]).strip(),
            issued_shares=int_or_none(r[col["發行股數(A)"]]),
            available_shares=int_or_none(r[col["僑外資及陸資尚可投資股數B=A*F-C"]]),
            held_shares=int_or_none(r[col["僑外資及陸資持有股數(C)"]]),
            available_pct=_percent(r[col["僑外資及陸資尚可投資比率(D=B/A)"]]),
            held_pct=_percent(r[col["僑外資及陸資持股比率(E=C/A)"]]),
            limit_pct=_percent(r[col["法令投資上限比率(F)"]]),
            note=str(r[col["備註"]]).strip(),
        ))
    return OtcForeignHoldingDay(date=served, holdings=holdings)
