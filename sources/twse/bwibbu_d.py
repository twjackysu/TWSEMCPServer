"""BWIBBU_d: 個股日本益比、殖利率及股價淨值比 — every listed stock's valuation on one day.

``GET https://www.twse.com.tw/rwd/zh/afterTrading/BWIBBU_d?response=json&selectType=ALL&date=20260930``
(no ``date`` = latest day). Reply: ``stat``, ``date`` (the day actually served, YYYYMMDD), ``title``,
``fields`` 證券代號, 證券名稱, 收盤價, 殖利率(%), 股利年度, 本益比, 股價淨值比, 財報年/季. 股利年度 is a JSON
number (ROC year), the rest are strings; 本益比 is "-" for loss-making companies.

A ``date`` the endpoint cannot parse is answered with the latest day rather than an error, so
callers compare the served ``date`` with the one they asked for. (The older
/exchangeReport/BWIBBU_ALL ignores ``date`` altogether and cannot serve history.)
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import List, Optional

from utils.api_client import TWSEAPIClient
from utils.errors import UpstreamFormatError
from utils.parse import decimal_or_none

from ..caching import day_cache_ttl
from ..columns import column_index

BWIBBU_D_URL = "https://www.twse.com.tw/rwd/zh/afterTrading/BWIBBU_d"
FIELDS = ("證券代號", "證券名稱", "收盤價", "殖利率(%)", "股利年度", "本益比", "股價淨值比", "財報年/季")


@dataclass(frozen=True)
class Valuation:
    code: str
    name: str
    close: Optional[Decimal]
    dividend_yield: Optional[Decimal]  # 殖利率(%)
    dividend_year: str                 # 股利年度, ROC year as published ("114")
    pe: Optional[Decimal]              # 本益比; None ("-") for loss-making companies
    pb: Optional[Decimal]              # 股價淨值比
    fiscal: str                        # 財報年/季, e.g. "115/2"


@dataclass(frozen=True)
class ValuationReport:
    stat: str    # "OK", or TWSE's reason for having nothing ("很抱歉，沒有符合條件的資料!")
    date: str    # YYYYMMDD actually served; "" when the reply names none
    title: str
    valuations: List[Valuation]

    @property
    def found(self) -> bool:
        return self.stat == "OK"


def valuation_ratios(client: TWSEAPIClient, date: str = "") -> ValuationReport:
    """Every listed stock's P/E, dividend yield and P/B on ``date`` (YYYYMMDD; "" = latest day)."""
    params = {"response": "json", "selectType": "ALL"}
    if date:
        params["date"] = date
    resp = client.fetch_json(BWIBBU_D_URL, params=params, cache_ttl=day_cache_ttl(date))
    if not isinstance(resp, dict):
        raise UpstreamFormatError(f"BWIBBU_d 回應不是 JSON 物件：{str(resp)[:120]}")
    stat, served, title = (str(resp.get(k) or "") for k in ("stat", "date", "title"))
    if stat != "OK" or not resp.get("data"):
        return ValuationReport(stat=stat, date=served, title=title, valuations=[])
    col = column_index(resp.get("fields"), FIELDS, "BWIBBU_d")
    valuations = [
        Valuation(
            code=str(r[col["證券代號"]]).strip(),
            name=str(r[col["證券名稱"]]).strip(),
            close=decimal_or_none(r[col["收盤價"]]),
            dividend_yield=decimal_or_none(r[col["殖利率(%)"]]),
            dividend_year=str(r[col["股利年度"]]).strip(),
            pe=decimal_or_none(r[col["本益比"]]),
            pb=decimal_or_none(r[col["股價淨值比"]]),
            fiscal=str(r[col["財報年/季"]]).strip(),
        )
        for r in resp["data"]
    ]
    return ValuationReport(stat=stat, date=served, title=title, valuations=valuations)
