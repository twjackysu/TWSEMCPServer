"""BFIAUU: 鉅額交易日成交資訊 — every listed block trade on one day.

``GET https://www.twse.com.tw/rwd/zh/block/BFIAUU?response=json&date=20250103`` (data from 2005-04-04;
no server-side filter by stock). Reply::

    {"stat": "OK", "date": "20250103", "title": "114年01月03日 鉅額交易日成交資訊-單一證券",
     "fields": ["證券代號", "證券名稱", "交易別", "成交價", "成交股數", "成交金額"],
     "data": [["2308", "台達電", "配對交易", "415.84", "287,920", "119,728,653"], ...,
              ["總計", "", "", "", "1,930,000", "1,321,887,680"]]}

Until 2011-12-16 a 交割期別 column ("T+2日交割") sits between 交易別 and 成交價 — seven columns, which made
unpacking six fail on every earlier date — so columns are found by name. The closing 總計 row (the day's
totals, in the code column) is left out. 成交金額 is 成交價 × 成交股數 rounded to the dollar.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import List, Optional

from utils.api_client import TWSEAPIClient
from utils.constants import SUMMARY_ROW_LABELS
from utils.errors import UpstreamFormatError
from utils.parse import decimal_or_none, int_or_none

from ..caching import day_cache_ttl
from ..columns import column_index

BFIAUU_URL = "https://www.twse.com.tw/rwd/zh/block/BFIAUU"
SOURCE = "BFIAUU"
FIELDS = ("證券代號", "證券名稱", "交易別", "成交價", "成交股數", "成交金額")
SETTLEMENT = "交割期別"  # until 2011-12-16


@dataclass(frozen=True)
class BlockTrade:
    code: str
    name: str
    kind: str                # 交易別: 配對交易, 逐筆交易, 盤後定價 …
    price: Optional[Decimal]  # 成交價
    volume: Optional[int]     # 成交股數
    value: Optional[int]      # 成交金額 (NT$)
    settlement: str          # 交割期別 ("T+2日交割") until 2011-12-16, else ""


@dataclass(frozen=True)
class BlockTradeDay:
    date: str    # YYYYMMDD
    title: str   # "114年01月03日 鉅額交易日成交資訊-單一證券"
    trades: List[BlockTrade]  # without the 總計 row; empty on a day without block trades


def block_trades(client: TWSEAPIClient, date: str) -> Optional[BlockTradeDay]:
    """Every listed block trade on ``date`` (YYYYMMDD), or None when TWSE has none (not a trading day,
    before 2005-04-04). Raises ``UpstreamFormatError`` if the reply's columns changed."""
    resp = client.fetch_json(BFIAUU_URL, params={"response": "json", "date": date}, cache_ttl=day_cache_ttl(date))
    if not isinstance(resp, dict):
        raise UpstreamFormatError(f"{SOURCE} 回應不是 JSON 物件：{str(resp)[:120]}")
    if resp.get("stat") != "OK":
        return None
    served, title = str(resp.get("date") or date), str(resp.get("title") or "")
    data = resp.get("data") or []
    if not data:
        return BlockTradeDay(date=served, title=title, trades=[])
    fields = [str(f).strip() for f in resp.get("fields") or []]
    col = column_index(fields, FIELDS + ((SETTLEMENT,) if SETTLEMENT in fields else ()), SOURCE)
    trades = []
    for r in data:
        if len(r) != len(fields):
            raise UpstreamFormatError(f"{SOURCE} 資料列有 {len(r)} 欄，欄位有 {len(fields)} 個：{r}")
        code = str(r[col["證券代號"]]).strip()
        if code in SUMMARY_ROW_LABELS:
            continue
        trades.append(BlockTrade(
            code=code,
            name=str(r[col["證券名稱"]]).strip(),
            kind=str(r[col["交易別"]]).strip(),
            price=decimal_or_none(r[col["成交價"]]),
            volume=int_or_none(r[col["成交股數"]]),
            value=int_or_none(r[col["成交金額"]]),
            settlement=str(r[col[SETTLEMENT]]).strip() if SETTLEMENT in col else "",
        ))
    return BlockTradeDay(date=served, title=title, trades=trades)
