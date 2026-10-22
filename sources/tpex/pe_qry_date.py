"""TPEx afterTrading/peQryDate: 上櫃股票個股本益比、殖利率、股價淨值比 — every OTC stock's valuation on one day.

``GET https://www.tpex.org.tw/www/zh-tw/afterTrading/peQryDate?date=2025/01/03&response=json``
(no ``date`` = latest day; data from 2007). Reply::

    {"date": "20250103", "stat": "ok",
     "tables": [{"fields": ["股票代號", "公司名稱", "本益比", "每股股利", "股利年度", "殖利率(%)", "股價淨值比", "財報年/季"],
                 "data": [["1240", "茂生農經        ", "11.78", "3.40000000", 113, "5.15", "1.17", "113Q3"], ...]}]}

財報年/季 only exists from 2025-01-02: before that the table has seven columns, which made reading the
eighth by position fail on every earlier date. 股利年度 is a JSON number (ROC year); names are padded
with spaces; numbers have no thousands separators (本益比 "11125.00"), and "N/A" where there is none.
A day without trading is an empty table.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import List, Optional

from utils.api_client import TWSEAPIClient
from utils.date_helper import slash_date
from utils.errors import UpstreamFormatError
from utils.parse import decimal_or_none

from ..caching import day_cache_ttl
from ..columns import column_index

PE_QRY_DATE_URL = "https://www.tpex.org.tw/www/zh-tw/afterTrading/peQryDate"
SOURCE = "afterTrading/peQryDate"
FIELDS = ("股票代號", "公司名稱", "本益比", "每股股利", "股利年度", "殖利率(%)", "股價淨值比")
FISCAL = "財報年/季"  # from 2025-01-02


@dataclass(frozen=True)
class OtcValuation:
    code: str
    name: str
    pe: Optional[Decimal]                  # 本益比; None ("N/A") without earnings
    dividend_per_share: Optional[Decimal]  # 每股股利 (NT$, published to eight decimals)
    dividend_year: str                     # 股利年度, ROC year as published ("113")
    dividend_yield: Optional[Decimal]      # 殖利率(%)
    pb: Optional[Decimal]                  # 股價淨值比; None ("N/A")
    fiscal: str                            # 財報年/季 ("113Q3"); "" before 2025-01-02


@dataclass(frozen=True)
class OtcValuationReport:
    date: str                     # the day TPEx answered for, YYYYMMDD
    valuations: List[OtcValuation]  # empty on a day without trading


def otc_valuation_ratios(client: TWSEAPIClient, date: str = "") -> OtcValuationReport:
    """Every OTC stock's P/E, dividend yield and P/B on ``date`` (YYYYMMDD; "" = latest day).
    Raises ``UpstreamFormatError`` if the reply's shape or columns changed."""
    params = {"response": "json"}
    if date:
        params["date"] = slash_date(date)
    resp = client.fetch_json(PE_QRY_DATE_URL, params=params, cache_ttl=day_cache_ttl(date))
    tables = resp.get("tables") if isinstance(resp, dict) else None
    if not isinstance(resp, dict) or not isinstance(tables, list):
        raise UpstreamFormatError(f"{SOURCE} 回應不再有 tables：{str(resp)[:120]}")
    served = str(resp.get("date") or "")
    table = tables[0] if tables and isinstance(tables[0], dict) else {}
    data = table.get("data") or []
    if not data:
        return OtcValuationReport(date=served, valuations=[])
    fields = [str(f).strip() for f in table.get("fields") or []]
    col = column_index(fields, FIELDS + ((FISCAL,) if FISCAL in fields else ()), SOURCE)
    valuations = []
    for r in data:
        if len(r) != len(fields):
            raise UpstreamFormatError(f"{SOURCE} 資料列有 {len(r)} 欄，欄位有 {len(fields)} 個：{r}")
        valuations.append(OtcValuation(
            code=str(r[col["股票代號"]]).strip(),
            name=str(r[col["公司名稱"]]).strip(),
            pe=decimal_or_none(r[col["本益比"]]),
            dividend_per_share=decimal_or_none(r[col["每股股利"]]),
            dividend_year=str(r[col["股利年度"]]).strip(),
            dividend_yield=decimal_or_none(r[col["殖利率(%)"]]),
            pb=decimal_or_none(r[col["股價淨值比"]]),
            fiscal=str(r[col[FISCAL]]).strip() if FISCAL in col else "",
        ))
    return OtcValuationReport(date=served, valuations=valuations)
