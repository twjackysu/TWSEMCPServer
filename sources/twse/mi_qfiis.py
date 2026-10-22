"""MI_QFIIS: 外資及陸資投資持股統計 — every listed security's foreign shareholding on one day.

``GET https://www.twse.com.tw/rwd/zh/fund/MI_QFIIS?response=json&selectType=ALLBUT0999&date=20250103`` (no ``date``
= the latest trading day). Reply::

    {"stat": "OK", "date": "20250103", "title": "114年01月03日 外資及陸資投資持股統計",
     "fields": ["證券代號", "證券名稱", "國際證券編碼", "發行股數", "外資及陸資尚可投資股數", "全體外資及陸資持有股數",
                "外資及陸資尚可投資比率", "全體外資及陸資持股比率", "外資及陸資共用法令投資上限比率", "陸資法令投資上限比率",
                "與前日異動原因(註)", "最近一次上市公司申報外資及陸資持股異動日期"],
     "data": [["0050", "元大台灣50", "TW0000050004", "2,219,000,000", "2,109,833,508", "109,166,492", 95.08, 4.91,
               "100.00", "100.00", "", "113/07/01"], ...]}

The two ratios are JSON numbers (4.6, 17.0), every other figure a string with thousands separators. Until
2009-04-30 the names say 外資 instead of 外資及陸資 (外資尚可投資股數, 全體外資持股比率, 法令投資上限比率) and there is no
陸資法令投資上限比率; mainland investors were admitted from 2009-05-04. Columns are found by the names of the era. A
day without trading answers ``stat`` OK with no rows.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, List, Optional

from utils.api_client import TWSEAPIClient
from utils.errors import UpstreamFormatError
from utils.parse import decimal_or_none, int_or_none

from ..caching import day_cache_ttl
from ..columns import column_index

MI_QFIIS_URL = "https://www.twse.com.tw/rwd/zh/fund/MI_QFIIS"
SOURCE = "MI_QFIIS"
# What each figure is called from 2009-05-04, and until 2009-04-30.
NAMES: Dict[str, tuple] = {
    "available_shares": ("外資及陸資尚可投資股數", "外資尚可投資股數"),
    "held_shares": ("全體外資及陸資持有股數", "全體外資持有股數"),
    "available_pct": ("外資及陸資尚可投資比率", "外資尚可投資比率"),
    "held_pct": ("全體外資及陸資持股比率", "全體外資持股比率"),
    "limit_pct": ("外資及陸資共用法令投資上限比率", "法令投資上限比率"),
}


@dataclass(frozen=True)
class ForeignHolding:
    code: str
    name: str
    issued_shares: Optional[int]      # 發行股數
    available_shares: Optional[int]   # 外資及陸資尚可投資股數
    held_shares: Optional[int]        # 全體外資及陸資持有股數
    available_pct: Optional[Decimal]  # 外資及陸資尚可投資比率 (%)
    held_pct: Optional[Decimal]       # 全體外資及陸資持股比率 (%)
    limit_pct: Optional[Decimal]      # 外資及陸資共用法令投資上限比率 (%); 法令投資上限比率 until 2009-04-30


@dataclass(frozen=True)
class ForeignHoldingDay:
    date: str                         # YYYYMMDD TWSE served
    holdings: List[ForeignHolding]    # empty on a day without trading


def foreign_holdings(client: TWSEAPIClient, date: str = "") -> Optional[ForeignHoldingDay]:
    """Every listed security's foreign shareholding on ``date`` (YYYYMMDD; "" = latest trading day), or None when
    TWSE answers with anything but OK. Raises ``UpstreamFormatError`` if the fields changed."""
    params = {"response": "json", "selectType": "ALLBUT0999"}
    if date:
        params["date"] = date
    resp = client.fetch_json(MI_QFIIS_URL, params=params, cache_ttl=day_cache_ttl(date))
    if not isinstance(resp, dict):
        raise UpstreamFormatError(f"{SOURCE} 回應不是 JSON 物件：{str(resp)[:120]}")
    if resp.get("stat") != "OK":
        return None
    served = str(resp.get("date") or date)
    data = resp.get("data") or []
    if not data:
        return ForeignHoldingDay(date=served, holdings=[])
    fields = [str(f).strip() for f in resp.get("fields") or []]
    era = 0 if NAMES["held_shares"][0] in fields else 1
    names = {attr: pair[era] for attr, pair in NAMES.items()}
    col = column_index(fields, ("證券代號", "證券名稱", "發行股數", *names.values()), SOURCE)
    at = {attr: col[name] for attr, name in names.items()}
    holdings = []
    for r in data:
        if len(r) != len(fields):
            raise UpstreamFormatError(f"{SOURCE} 資料列有 {len(r)} 欄，欄位有 {len(fields)} 個：{r}")
        holdings.append(ForeignHolding(
            code=str(r[col["證券代號"]]).strip(),
            name=str(r[col["證券名稱"]]).strip(),
            issued_shares=int_or_none(r[col["發行股數"]]),
            available_shares=int_or_none(r[at["available_shares"]]),
            held_shares=int_or_none(r[at["held_shares"]]),
            available_pct=decimal_or_none(r[at["available_pct"]]),
            held_pct=decimal_or_none(r[at["held_pct"]]),
            limit_pct=decimal_or_none(r[at["limit_pct"]]),
        ))
    return ForeignHoldingDay(date=served, holdings=holdings)
