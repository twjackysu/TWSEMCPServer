"""MI_INDEX: TWSE's after-close report for one trading day — per-stock quotes and the index board.

``GET https://www.twse.com.tw/rwd/zh/afterTrading/MI_INDEX?response=json&type=<type>[&date=YYYYMMDD]``
(no ``date`` = latest trading day). The reply has ``stat``, ``date`` (the day it covers) and a
``tables`` list; each table has ``title``, ``fields`` and ``data``. Which tables come back depends on
``type``:

- ``ALLBUT0999`` (all except warrants/CBBCs) or a two-digit industry code (``24`` = 半導體業): a
  quote table titled "115年09月30日 每日收盤行情(全部(不含權證、牛熊證、可展延牛熊證))" /
  "…每日收盤行情(半導體業)" with columns 證券代號, 證券名稱, 成交股數, 成交筆數, 成交金額, 開盤價,
  最高價, 最低價, 收盤價, 漲跌(+/-), 漲跌價差, 最後揭示買/賣價/量, 本益比. 漲跌(+/-) is HTML
  (``<p style= color:red>+</p>``, ``-``, blank, ``X`` = 除權息) and 漲跌價差 is unsigned. Prices are "--"
  without trades; 本益比 can be "" in industry tables.
- ``IND``: index tables (價格指數／報酬指數 × 臺灣證券交易所／跨市場／臺灣指數公司) with columns
  指數 (報酬指數 in the return tables), 收盤指數, 漲跌(+/-) (HTML), 漲跌點數 (unsigned),
  漲跌百分比(%) (signed), 特殊處理註記.

A non-trading day answers with another ``stat`` and no tables.
"""

import re
from dataclasses import dataclass
from decimal import Decimal
from typing import List, Optional

from utils.api_client import TWSEAPIClient
from utils.errors import UpstreamFormatError
from utils.parse import decimal_or_none, int_or_none

from ..caching import day_cache_ttl
from ..columns import column_index

MI_INDEX_URL = "https://www.twse.com.tw/rwd/zh/afterTrading/MI_INDEX"
QUOTE_TABLE_MARK = "每日收盤行情"
QUOTE_FIELDS = ("證券代號", "證券名稱", "成交股數", "成交筆數", "成交金額", "開盤價", "最高價", "最低價", "收盤價",
                "漲跌(+/-)", "漲跌價差", "本益比")
INDEX_FIELDS = ("收盤指數", "漲跌(+/-)", "漲跌點數", "漲跌百分比(%)")

_TAG_RE = re.compile(r"<[^>]+>")
_GROUP_RE = re.compile(re.escape(QUOTE_TABLE_MARK) + r"\((.*)\)\s*$")


def strip_tags(value) -> str:
    """The text of an HTML cell: "<p style= color:red>+</p>" → "+"."""
    return _TAG_RE.sub("", str(value)).strip()


def _signed(direction: str, points: Optional[Decimal]) -> Optional[Decimal]:
    return -points if points is not None and direction == "-" else points


@dataclass(frozen=True)
class StockQuote:
    code: str
    name: str
    volume: Optional[int]          # 成交股數
    transactions: Optional[int]    # 成交筆數
    value: Optional[int]           # 成交金額 (NT$)
    open: Optional[Decimal]        # Decimal keeps the printed digits; None on "--"
    high: Optional[Decimal]
    low: Optional[Decimal]
    close: Optional[Decimal]
    direction: str                 # 漲跌(+/-) without its HTML: "+", "-", "" (unchanged) or "X" (除權息)
    change_points: Optional[Decimal]  # 漲跌價差, unsigned as published
    pe: Optional[Decimal]          # 本益比; None when blank

    @property
    def change(self) -> Optional[Decimal]:
        """漲跌價差 with its sign (negative when the direction is "-")."""
        return _signed(self.direction, self.change_points)


@dataclass(frozen=True)
class QuoteTable:
    date: str                      # YYYYMMDD of the day the reply covers
    title: str
    group: str                     # what the title's 每日收盤行情(…) names: "半導體業", "全部(…)"
    quotes: List[StockQuote]


@dataclass(frozen=True)
class IndexQuote:
    name: str
    close: Optional[Decimal]
    direction: str                 # "+" / "-" / ""
    change_points: Optional[Decimal]  # unsigned as published
    change_pct: Optional[Decimal]  # signed as published
    note: str                      # 特殊處理註記

    @property
    def change(self) -> Optional[Decimal]:
        return _signed(self.direction, self.change_points)


@dataclass(frozen=True)
class IndexTable:
    title: str                     # "115年09月30日 價格指數(臺灣證券交易所)", "報酬指數(跨市場)", …
    quotes: List[IndexQuote]


@dataclass(frozen=True)
class IndexBoard:
    date: str                      # YYYYMMDD of the day the reply covers
    tables: List[IndexTable]


def _fetch(client: TWSEAPIClient, select: str, date: str) -> Optional[dict]:
    params = {"response": "json", "type": select}
    if date:
        params["date"] = date
    resp = client.fetch_json(MI_INDEX_URL, params=params, cache_ttl=day_cache_ttl(date))
    if not isinstance(resp, dict):
        raise UpstreamFormatError(f"MI_INDEX 回應不是 JSON 物件：{str(resp)[:120]}")
    return resp if resp.get("stat") == "OK" else None


def stock_quotes(client: TWSEAPIClient, select: str = "ALLBUT0999", date: str = "") -> Optional[QuoteTable]:
    """The 每日收盤行情 table for ``select`` (ALLBUT0999 or an industry code) on ``date``
    (YYYYMMDD, "" = latest). None when TWSE has none (not a trading day, no such group)."""
    resp = _fetch(client, select, date)
    if resp is None:
        return None
    table = next((t for t in resp.get("tables") or [] if QUOTE_TABLE_MARK in (t.get("title") or "")), None)
    if not table or not table.get("data"):
        return None
    col = column_index(table.get("fields"), QUOTE_FIELDS, "MI_INDEX 每日收盤行情")
    quotes = [
        StockQuote(
            code=str(r[col["證券代號"]]).strip(),
            name=str(r[col["證券名稱"]]).strip(),
            volume=int_or_none(r[col["成交股數"]]),
            transactions=int_or_none(r[col["成交筆數"]]),
            value=int_or_none(r[col["成交金額"]]),
            open=decimal_or_none(r[col["開盤價"]]),
            high=decimal_or_none(r[col["最高價"]]),
            low=decimal_or_none(r[col["最低價"]]),
            close=decimal_or_none(r[col["收盤價"]]),
            direction=strip_tags(r[col["漲跌(+/-)"]]),
            change_points=decimal_or_none(r[col["漲跌價差"]]),
            pe=decimal_or_none(r[col["本益比"]]),
        )
        for r in table["data"]
    ]
    title = str(table.get("title") or "")
    group = _GROUP_RE.search(title)
    return QuoteTable(date=str(resp.get("date") or date), title=title, group=group.group(1) if group else "",
                      quotes=quotes)


def index_quotes(client: TWSEAPIClient, date: str = "") -> Optional[IndexBoard]:
    """Every index table (type=IND) on ``date`` (YYYYMMDD, "" = latest), or None on a non-trading day."""
    resp = _fetch(client, "IND", date)
    if resp is None:
        return None
    tables = []
    for t in resp.get("tables") or []:
        title, rows = t.get("title"), t.get("data") or []
        if not title or not rows:
            continue  # IND also returns empty placeholder tables
        # The name column is 指數 or 報酬指數 — always the first one.
        col = column_index(t.get("fields"), INDEX_FIELDS, f"MI_INDEX 指數表「{title}」")
        fields = [str(f).strip() for f in t.get("fields") or []]
        note_at = fields.index("特殊處理註記") if "特殊處理註記" in fields else None
        tables.append(IndexTable(title=str(title), quotes=[
            IndexQuote(
                name=str(r[0]).strip(),
                close=decimal_or_none(r[col["收盤指數"]]),
                direction=strip_tags(r[col["漲跌(+/-)"]]),
                change_points=decimal_or_none(r[col["漲跌點數"]]),
                change_pct=decimal_or_none(r[col["漲跌百分比(%)"]]),
                note="" if note_at is None else str(r[note_at]).strip(),
            )
            for r in rows
        ]))
    return IndexBoard(date=str(resp.get("date") or date), tables=tables)
