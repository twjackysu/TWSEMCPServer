"""TDCC 集保戶股權分散表查詢 page: one security's distribution for any of the last ~51 weeks.

``https://www.tdcc.com.tw/portal/zh/smWeb/qryStock`` is a stateful form without a CAPTCHA. GET the page (sets the
JSESSIONID cookie; hidden ``SYNCHRONIZER_TOKEN`` and ``firDate``, and a ``scaDate`` select of the weeks, newest
first), then POST one week at a time with ``SYNCHRONIZER_TOKEN``, ``SYNCHRONIZER_URI``, ``method=submit``,
``firDate``, ``scaDate``, ``sqlMethod=StockNo``, ``stockNo`` and ``stockName``. A token works once; every reply
carries the next one. The reply's table::

    序 | 持股/單位數分級 | 人數 | 股數/單位數 | 占集保庫存數比例 (%)
    1 | 1-999 | 2,459,344 | 287,438,824 | 1.10
    …
    15 | 1,000,001以上 | 1,482 | 21,987,181,886 | 84.78
    16 | 差異數調整（說明4） |  | -6,000 | -0.00
    17 | 合　計 | 3,007,088 | 25,932,370,067 | 100.00

差異數調整 is left out when it is zero, and 合計 is then 序 16. An unknown code or a week without data is the same
table with a single 查無此資料 cell.
"""

import re
from dataclasses import dataclass
from typing import List, Optional, Tuple

import requests

from utils.api_client import TWSEAPIClient
from utils.errors import UpstreamFormatError
from utils.parse import decimal_or_none, int_or_none

from ..columns import column_index
from .levels import TOTAL, LevelHolding

URL = "https://www.tdcc.com.tw/portal/zh/smWeb/qryStock"
# A browser-like User-Agent, as for the other website flows.
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
SOURCE = "集保查詢頁"
NO_DATA_TEXT = "查無此資料"
FIELDS = ("序", "持股/單位數分級", "人數", "股數/單位數", "占集保庫存數比例 (%)")

TOKEN_RE = re.compile(r'name="SYNCHRONIZER_TOKEN" value="([^"]+)"')
_FIRST_DATE_RE = re.compile(r'name="firDate" value="(\d+)"')
_DATE_SELECT_RE = re.compile(r'<select name="scaDate".*?</select>', re.S)
_TABLE_RE = re.compile(r"<table.*?</table>", re.S)
_ROW_RE = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S)
_CELL_RE = re.compile(r"<t[dh][^>]*>(.*?)</t[dh]>", re.S)
_TAG_RE = re.compile(r"<[^>]+>")


@dataclass(frozen=True)
class WeekDistribution:
    levels: List[LevelHolding]  # 持股分級 1–15 and 合計 (level TOTAL); 差異數調整 is left out (see sources.tdcc.levels)

    @property
    def total(self) -> LevelHolding:
        return next(h for h in self.levels if h.level == TOTAL)


def _levels(html: str) -> List[LevelHolding]:
    """The result table's rows, found by its header; [] when the page has no such table."""
    for table in _TABLE_RE.findall(html):
        rows = [[_TAG_RE.sub("", c).strip() for c in _CELL_RE.findall(r)] for r in _ROW_RE.findall(table)]
        head = next((i for i, r in enumerate(rows) if "持股/單位數分級" in r), None)
        if head is None:
            continue
        col = column_index(rows[head], FIELDS, SOURCE)
        levels = []
        for r in rows[head + 1:]:
            if len(r) != len(rows[head]):
                continue  # the single 查無此資料 cell
            label = r[col["持股/單位數分級"]]
            if label.startswith("差異數調整"):
                continue
            level = TOTAL if label.startswith("合") else int_or_none(r[col["序"]])
            people, shares = int_or_none(r[col["人數"]]), int_or_none(r[col["股數/單位數"]])
            pct = decimal_or_none(r[col["占集保庫存數比例 (%)"]])
            if level is None or people is None or shares is None or pct is None:
                raise UpstreamFormatError(f"{SOURCE} 結果表的數字格式已變更：{r}")
            levels.append(LevelHolding(level=level, people=people, shares=shares, pct=pct))
        return levels
    return []


class StockQuery:
    """One session of the query page: the weeks it offers, then one week's distribution at a time (each POST
    uses the token the previous reply issued). Not shared between threads: every tool call opens its own."""

    def __init__(self, client: TWSEAPIClient):
        self._client = client
        self._session = requests.Session()
        self._token, self.first_date, self.dates = self._load()

    def _load(self) -> Tuple[str, str, List[str]]:
        """(one-time token, newest week, selectable weeks newest first) from a fresh copy of the page."""
        html = self._client.fetch_bytes(URL, headers=HEADERS, timeout=60, session=self._session).decode(
            "utf-8", errors="replace")
        token, first = TOKEN_RE.search(html), _FIRST_DATE_RE.search(html)
        select = _DATE_SELECT_RE.search(html)
        dates = re.findall(r'<option[^>]*value="?(\d{8})', select.group(0)) if select else []
        if not (token and first and dates):
            raise UpstreamFormatError("集保查詢頁結構與預期不符（找不到 token 或日期清單），頁面可能改版")
        return token.group(1), first.group(1), dates

    def week(self, code: str, date: str) -> Optional[WeekDistribution]:
        """``code``'s distribution in week ``date`` (one of ``dates``), or None when TDCC answers 查無此資料. Raises
        ``UpstreamFormatError`` on a reply with neither the table nor that notice (an error page or a redesign)."""
        html = self._client.fetch_bytes(
            URL, method="POST", headers=HEADERS, timeout=60, session=self._session,
            data={"SYNCHRONIZER_TOKEN": self._token, "SYNCHRONIZER_URI": "/portal/zh/smWeb/qryStock",
                  "method": "submit", "firDate": self.first_date, "scaDate": date,
                  "sqlMethod": "StockNo", "stockNo": code, "stockName": ""},
        ).decode("utf-8", errors="replace")
        nxt = TOKEN_RE.search(html)
        # Each token works once; if the reply carries none, reload the page for a fresh one.
        self._token = nxt.group(1) if nxt else self._load()[0]
        levels = _levels(html)
        if any(h.level == TOTAL for h in levels):
            return WeekDistribution(levels)
        if NO_DATA_TEXT in html:
            return None
        raise UpstreamFormatError(f"集保查詢頁 {date} 週的回應無法解析（頁面可能改版或暫時無法使用）")
