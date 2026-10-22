"""TPEx bulletin/exDailyQ: 除權除息計算結果 — what each OTC security's ex-rights / ex-dividend day worked out to.

``GET https://www.tpex.org.tw/www/zh-tw/bulletin/exDailyQ?startDate=2025/01/01&endDate=2025/12/31&response=json``
(no dates = today and the next trading day, whose results are published a day ahead). Reply::

    {"date": "20250101~20251231", "stat": "ok",
     "tables": [{"fields": ["除權息日期", "代號", "名稱", "除權息前收盤價", "除權息參考價", "權值", "息值", "權值+息值",
                            "權/息", "漲停價", "跌停價", "開始交易基準價", "減除股利參考價", "現金股利", "每仟股無償配股",
                            "現金增資股數", "現金增資認購價", "公開承銷股數", "員工認購股數", "原股東認購股數",
                            "按持股比例仟股認購"],
                 "data": [["114/12/31", "6561", "是方              ", "392.50", "385.90", "0.000000", "6.600000",
                           "6.600000", "除息", "424.00", "347.50", "386.00", "385.90", "6.60000000", ...], ...]}]}

A range that starts before 2016 gets one more column, 員工紅利轉增資, before 現金增資股數 — on every row, those
from 2016 on too — so columns are found by name. Names are padded with spaces; numbers have no thousands
separators and up to eight decimals. A range without results is an empty table; a start after the end
answers ``{"stat": "參數錯誤"}`` with no table, which is passed on like TWT49U's ``stat``.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import List, Optional

from utils.api_client import TWSEAPIClient
from utils.date_helper import parse_roc_date, slash_date
from utils.errors import UpstreamFormatError
from utils.parse import decimal_or_none, int_or_none

from ..caching import day_cache_ttl
from ..columns import column_index

EX_DAILY_Q_URL = "https://www.tpex.org.tw/www/zh-tw/bulletin/exDailyQ"
SOURCE = "bulletin/exDailyQ"
FIELDS = ("除權息日期", "代號", "名稱", "除權息前收盤價", "除權息參考價", "權值", "息值", "權/息", "漲停價", "跌停價",
          "開始交易基準價", "現金股利", "每仟股無償配股", "現金增資股數", "現金增資認購價")


@dataclass(frozen=True)
class OtcExRightResult:
    day: date
    code: str
    name: str
    close_before: Optional[Decimal]        # 除權息前收盤價
    reference: Optional[Decimal]           # 除權息參考價 (= close_before - rights - dividend, to the cent)
    rights: Optional[Decimal]              # 權值
    dividend: Optional[Decimal]            # 息值
    kind: str                              # 權/息: "除權", "除息" or "除權息"
    limit_up: Optional[Decimal]            # 漲停價
    limit_down: Optional[Decimal]          # 跌停價
    opening_reference: Optional[Decimal]   # 開始交易基準價
    cash_dividend: Optional[Decimal]       # 現金股利 (NT$ per share)
    stock_dividend: Optional[Decimal]      # 每仟股無償配股 (shares per 1,000 held)
    cash_capital_shares: Optional[int]     # 現金增資股數 (0 when there is none)
    cash_capital_price: Optional[Decimal]  # 現金增資認購價


@dataclass(frozen=True)
class OtcExRightReport:
    stat: str                     # "ok", or TPEx's reason for answering nothing ("參數錯誤")
    period: str                   # the range answered, as published: "20250101~20251231"; "" with no table
    results: List[OtcExRightResult]


def otc_exright_results(client: TWSEAPIClient, start: Optional[date] = None,
                        end: Optional[date] = None) -> OtcExRightReport:
    """Every OTC ex-rights / ex-dividend result between ``start`` and ``end`` (inclusive); both None =
    today and the next trading day. Raises ``UpstreamFormatError`` if the reply's shape or columns changed."""
    params = {"response": "json"}
    if start and end:
        params.update(startDate=slash_date(f"{start:%Y%m%d}"), endDate=slash_date(f"{end:%Y%m%d}"))
    resp = client.fetch_json(EX_DAILY_Q_URL, params=params, cache_ttl=day_cache_ttl(f"{end:%Y%m%d}" if end else ""))
    if not isinstance(resp, dict):
        raise UpstreamFormatError(f"{SOURCE} 回應不是 JSON 物件：{str(resp)[:120]}")
    stat, period, tables = str(resp.get("stat") or ""), str(resp.get("date") or ""), resp.get("tables")
    if not isinstance(tables, list):
        if stat != "ok":
            return OtcExRightReport(stat=stat, period=period, results=[])
        raise UpstreamFormatError(f"{SOURCE} 回應不再有 tables：{str(resp)[:120]}")
    table = tables[0] if tables and isinstance(tables[0], dict) else {}
    data = table.get("data") or []
    if not data:
        return OtcExRightReport(stat=stat, period=period, results=[])
    fields = [str(f).strip() for f in table.get("fields") or []]
    col = column_index(fields, FIELDS, SOURCE)
    results = []
    for r in data:
        if len(r) != len(fields):
            raise UpstreamFormatError(f"{SOURCE} 資料列有 {len(r)} 欄，欄位有 {len(fields)} 個：{r}")
        day = parse_roc_date(r[col["除權息日期"]])
        if day is None:
            raise UpstreamFormatError(f"{SOURCE} 除權息日期格式已變更：{r[col['除權息日期']]!r}")
        results.append(OtcExRightResult(
            day=day,
            code=str(r[col["代號"]]).strip(),
            name=str(r[col["名稱"]]).strip(),
            close_before=decimal_or_none(r[col["除權息前收盤價"]]),
            reference=decimal_or_none(r[col["除權息參考價"]]),
            rights=decimal_or_none(r[col["權值"]]),
            dividend=decimal_or_none(r[col["息值"]]),
            kind=str(r[col["權/息"]]).strip(),
            limit_up=decimal_or_none(r[col["漲停價"]]),
            limit_down=decimal_or_none(r[col["跌停價"]]),
            opening_reference=decimal_or_none(r[col["開始交易基準價"]]),
            cash_dividend=decimal_or_none(r[col["現金股利"]]),
            stock_dividend=decimal_or_none(r[col["每仟股無償配股"]]),
            cash_capital_shares=int_or_none(r[col["現金增資股數"]]),
            cash_capital_price=decimal_or_none(r[col["現金增資認購價"]]),
        ))
    return OtcExRightReport(stat=stat, period=period, results=results)
