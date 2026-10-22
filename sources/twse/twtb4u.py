"""TWTB4U: 當日沖銷交易標的及成交量值 — the day-trading list of one day, with the market totals.

``GET https://www.twse.com.tw/rwd/zh/dayTrading/TWTB4U?response=json&selectType=All&date=20250103`` (no ``date`` =
the latest trading day; from 2014-01-06 — earlier dates answer ``stat`` 查詢日期小於103年1月6日). Reply::

    {"stat": "OK", "date": "20250103", "tables": [
      {"title": "114年01月03日 當日沖銷交易統計資訊",
       "fields": ["當日沖銷交易總成交股數", "當日沖銷交易總成交股數占市場比重%", "當日沖銷交易總買進成交金額",
                  "當日沖銷交易總買進成交金額占市場比重%", "當日沖銷交易總賣出成交金額", "當日沖銷交易總賣出成交金額占市場比重%"],
       "data": [["1,336,093,000", "21.55", "126,279,376,690", "37.46", "126,483,285,690", "37.52"]]},
      {"title": "114年01月03日 當日沖銷交易標的及成交量值",
       "fields": ["證券代號", "證券名稱", "暫停現股賣出後現款買進當沖註記", "當日沖銷交易成交股數",
                  "當日沖銷交易買進成交金額", "當日沖銷交易賣出成交金額"],
       "data": [["0050", "元大台灣50", "", "269,000", "52,719,950", "52,751,400"], ...]}]}

TWSE publishes the figures in the evening. Before that, the latest day's first table is empty and the second is
the list only (當日沖銷交易標的: 證券代號, 證券名稱, and the 註記 written with a line break). Tables are found by
their fields; same fields checked 2015–2026.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Dict, List, Optional

from utils.api_client import TWSEAPIClient
from utils.errors import UpstreamFormatError
from utils.parse import decimal_or_none, int_or_none

from ..caching import day_cache_ttl
from ..columns import column_index

TWTB4U_URL = "https://www.twse.com.tw/rwd/zh/dayTrading/TWTB4U"
SOURCE = "TWTB4U"
SUMMARY_FIELDS = ("當日沖銷交易總成交股數", "當日沖銷交易總成交股數占市場比重%", "當日沖銷交易總買進成交金額",
                  "當日沖銷交易總買進成交金額占市場比重%", "當日沖銷交易總賣出成交金額", "當日沖銷交易總賣出成交金額占市場比重%")
TARGET_FIELDS = ("證券代號", "證券名稱", "暫停現股賣出後現款買進當沖註記")
# Only once the day's figures are published.
VOLUME_FIELDS = ("當日沖銷交易成交股數", "當日沖銷交易買進成交金額", "當日沖銷交易賣出成交金額")


@dataclass(frozen=True)
class DayTradingSummary:
    volume: Optional[int]          # 當日沖銷交易總成交股數
    volume_pct: Optional[Decimal]  # 占市場比重 (%)
    buy_value: Optional[int]       # 當日沖銷交易總買進成交金額 (元)
    buy_pct: Optional[Decimal]
    sell_value: Optional[int]      # 當日沖銷交易總賣出成交金額 (元)
    sell_pct: Optional[Decimal]


@dataclass(frozen=True)
class DayTradingTarget:
    code: str
    name: str
    sell_first_suspended: bool     # 暫停現股賣出後現款買進當沖註記 = "Y"
    volume: Optional[int]          # 當日沖銷交易成交股數; None before the evening publication
    buy_value: Optional[int]       # 當日沖銷交易買進成交金額 (元)
    sell_value: Optional[int]      # 當日沖銷交易賣出成交金額 (元)


@dataclass(frozen=True)
class DayTradingReport:
    date: str                              # YYYYMMDD TWSE served
    summary: Optional[DayTradingSummary]   # None before the evening publication
    targets: List[DayTradingTarget]
    published: bool                        # the targets carry the day's figures


def _fields(table: Dict[str, Any]) -> List[str]:
    return ["".join(str(f).split()) for f in table.get("fields") or []]


def _rows(table: Dict[str, Any], fields: List[str]) -> List[List[Any]]:
    rows = table.get("data") or []
    for r in rows:
        if len(r) != len(fields):
            raise UpstreamFormatError(f"{SOURCE} 資料列有 {len(r)} 欄，欄位有 {len(fields)} 個：{r}")
    return rows


def day_trading(client: TWSEAPIClient, date: str = "") -> Optional[DayTradingReport]:
    """The day-trading list of ``date`` (YYYYMMDD; "" = latest trading day), or None when TWSE has none (not a
    trading day, before 2014-01-06). Raises ``UpstreamFormatError`` if the tables' fields changed."""
    params = {"selectType": "All", "response": "json"}
    if date:
        params["date"] = date
    resp = client.fetch_json(TWTB4U_URL, params=params, cache_ttl=day_cache_ttl(date))
    if not isinstance(resp, dict):
        raise UpstreamFormatError(f"{SOURCE} 回應不是 JSON 物件：{str(resp)[:120]}")
    if resp.get("stat") != "OK":
        return None
    tables = [t for t in resp.get("tables") or [] if isinstance(t, dict)]
    target_table = next((t for t in tables if "證券代號" in _fields(t)), None)
    if target_table is None:
        if any(t.get("data") for t in tables):
            raise UpstreamFormatError(f"{SOURCE} 找不到當沖標的表（有「證券代號」欄位的表）：{[_fields(t) for t in tables]}")
        return None

    summary = None
    summary_table = next((t for t in tables if SUMMARY_FIELDS[0] in _fields(t)), None)
    if summary_table is not None:
        fields = _fields(summary_table)
        rows = _rows(summary_table, fields)
        if rows:
            col = column_index(fields, SUMMARY_FIELDS, SOURCE)
            s = rows[0]
            summary = DayTradingSummary(
                volume=int_or_none(s[col[SUMMARY_FIELDS[0]]]),
                volume_pct=decimal_or_none(s[col[SUMMARY_FIELDS[1]]]),
                buy_value=int_or_none(s[col[SUMMARY_FIELDS[2]]]),
                buy_pct=decimal_or_none(s[col[SUMMARY_FIELDS[3]]]),
                sell_value=int_or_none(s[col[SUMMARY_FIELDS[4]]]),
                sell_pct=decimal_or_none(s[col[SUMMARY_FIELDS[5]]]),
            )

    fields = _fields(target_table)
    published = any(f in fields for f in VOLUME_FIELDS)
    col = column_index(fields, TARGET_FIELDS + (VOLUME_FIELDS if published else ()), SOURCE)
    targets = [DayTradingTarget(
        code=str(r[col["證券代號"]]).strip(),
        name=str(r[col["證券名稱"]]).strip(),
        sell_first_suspended=str(r[col["暫停現股賣出後現款買進當沖註記"]]).strip() == "Y",
        volume=int_or_none(r[col["當日沖銷交易成交股數"]]) if published else None,
        buy_value=int_or_none(r[col["當日沖銷交易買進成交金額"]]) if published else None,
        sell_value=int_or_none(r[col["當日沖銷交易賣出成交金額"]]) if published else None,
    ) for r in _rows(target_table, fields)]
    return DayTradingReport(date=str(resp.get("date") or date), summary=summary, targets=targets, published=published)
