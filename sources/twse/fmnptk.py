"""FMNPTK: 個股年成交資訊 — one listed security's trading summed per year, oldest first (ROC 80 for 1101, 83 for 2330).

``GET https://www.twse.com.tw/rwd/zh/afterTrading/FMNPTK?response=json&stockNo=2330&date=20261022`` (the series ends
with the year of ``date``). Reply::

    {"stat": "OK", "tables": [
      {"title": "2330 台積電           年度 成交資訊",
       "fields": ["年度", "成交股數", "成交金額", "成交筆數", "最高價", "日期", "最低價", "日期", "收盤平均價"],
       "data": [[83, "260,767,893", "43,077,714,614", "90,627", "177.00", "10/05", "96.00", "9/05", "159.04"], ...]},
      {"fields": ["近年最高價", "日期", "近年最低價", "日期"], "data": [["1,550.00", "114/12/31", "34.90", "91/10/08"]]}]}

The yearly table has two 日期 columns and no ``groups``: each is the day (M/DD) of the price before it, so it is
named after that price ("最高價/日期"). 年度 (ROC) is a JSON number. The second table (all-time high and low) is not
read. A code TWSE does not list answers another ``stat``.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import List, Optional

from utils.api_client import TWSEAPIClient
from utils.errors import UpstreamFormatError
from utils.parse import decimal_or_none, int_or_none

from ..caching import year_cache_ttl
from ..columns import column_index

FMNPTK_URL = "https://www.twse.com.tw/rwd/zh/afterTrading/FMNPTK"
SOURCE = "FMNPTK"
FIELDS = ("年度", "成交股數", "成交金額", "成交筆數", "最高價", "最高價/日期", "最低價", "最低價/日期", "收盤平均價")


@dataclass(frozen=True)
class YearlyTrading:
    year: int                        # 年度 (ROC)
    volume: Optional[int]            # 成交股數
    value: Optional[int]             # 成交金額 (元)
    transactions: Optional[int]      # 成交筆數
    high: Optional[Decimal]          # 最高價
    high_date: str                   # its day, M/DD as published ("10/05")
    low: Optional[Decimal]           # 最低價
    low_date: str
    average_close: Optional[Decimal]  # 收盤平均價


def _names(fields: List[str]) -> List[str]:
    """A 日期 column is named after the price before it: 最高價, 日期 → 最高價, 最高價/日期."""
    return [f"{fields[i - 1]}/{f}" if f == "日期" and i else f for i, f in enumerate(fields)]


def yearly_trading(client: TWSEAPIClient, code: str, date: str) -> Optional[List[YearlyTrading]]:
    """``code``'s yearly trading up to the year of ``date`` (YYYYMMDD), oldest first, or None when TWSE has none
    (not a listed code). Raises ``UpstreamFormatError`` if the reply changed."""
    resp = client.fetch_json(FMNPTK_URL, params={"response": "json", "date": date, "stockNo": code},
                             cache_ttl=year_cache_ttl(int(date[:4])))
    if not isinstance(resp, dict):
        raise UpstreamFormatError(f"{SOURCE} 回應不是 JSON 物件：{str(resp)[:120]}")
    if resp.get("stat") != "OK":
        return None
    tables = [t for t in resp.get("tables") or [] if isinstance(t, dict)]
    table = next((t for t in tables if "年度" in (t.get("fields") or [])), None)
    if table is None:
        if any(t.get("data") for t in tables):
            raise UpstreamFormatError(f"{SOURCE} 找不到年度成交表（有「年度」欄位的表）：{[t.get('fields') for t in tables]}")
        return []
    fields = _names([str(f).strip() for f in table.get("fields") or []])
    col = column_index(fields, FIELDS, SOURCE)
    years = []
    for r in table.get("data") or []:
        if len(r) != len(fields):
            raise UpstreamFormatError(f"{SOURCE} 資料列有 {len(r)} 欄，欄位有 {len(fields)} 個：{r}")
        roc_year = int_or_none(r[col["年度"]])
        if roc_year is None:
            raise UpstreamFormatError(f"{SOURCE} 年度格式已變更：{r}")
        years.append(YearlyTrading(
            year=roc_year,
            volume=int_or_none(r[col["成交股數"]]),
            value=int_or_none(r[col["成交金額"]]),
            transactions=int_or_none(r[col["成交筆數"]]),
            high=decimal_or_none(r[col["最高價"]]),
            high_date=str(r[col["最高價/日期"]]).strip(),
            low=decimal_or_none(r[col["最低價"]]),
            low_date=str(r[col["最低價/日期"]]).strip(),
            average_close=decimal_or_none(r[col["收盤平均價"]]),
        ))
    return years
