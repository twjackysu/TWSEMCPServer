"""TWT49U: 除權除息計算結果 — what each listed security's ex-rights / ex-dividend day worked out to.

``GET https://www.twse.com.tw/rwd/zh/exRight/TWT49U?response=json&startDate=20260101&endDate=20260930``
Reply ``fields``: 資料日期, 股票代號, 股票名稱, 除權息前收盤價, 除權息參考價, 權值+息值, 權/息, 漲停價格,
跌停價格, 開盤競價基準, 減除股利參考價, 詳細資料, 最近一次申報資料 季別/日期, 最近一次申報每股 (單位)淨值,
最近一次申報每股 (單位)盈餘. Dates are "115年03月17日". The last two hold "" (nothing filed) or "N/A"
(not applicable, e.g. ETFs) where there is no number.

When there is nothing to report ``stat`` says why in TWSE's own words — "很抱歉，沒有符合條件的資料!",
"開始日期大於結束日期，請重新查詢!" — which callers pass on.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import List, Optional

from utils.api_client import TWSEAPIClient
from utils.date_helper import parse_roc_date
from utils.errors import UpstreamFormatError
from utils.parse import decimal_or_none

from ..caching import day_cache_ttl
from ..columns import column_index

TWT49U_URL = "https://www.twse.com.tw/rwd/zh/exRight/TWT49U"
FIELDS = ("資料日期", "股票代號", "股票名稱", "除權息前收盤價", "除權息參考價", "權值+息值", "權/息", "漲停價格",
          "跌停價格", "開盤競價基準", "減除股利參考價", "最近一次申報每股 (單位)淨值", "最近一次申報每股 (單位)盈餘")


@dataclass(frozen=True)
class ExRightResult:
    day: date
    code: str
    name: str
    close_before: Optional[Decimal]         # 除權息前收盤價
    reference: Optional[Decimal]            # 除權息參考價
    rights_and_dividend: Optional[Decimal]  # 權值+息值 (published to six decimals, e.g. 6.000035)
    kind: str                               # 權/息: "權", "息" or "權息"
    limit_up: Optional[Decimal]             # 漲停價格
    limit_down: Optional[Decimal]           # 跌停價格
    opening_reference: Optional[Decimal]    # 開盤競價基準
    ex_dividend_reference: Optional[Decimal]  # 減除股利參考價
    nav_per_share: str                      # 最近一次申報每股淨值 as published: "248.05", "" or "N/A"
    eps: str                                # 最近一次申報每股盈餘 as published: "49.33", "" or "N/A"


@dataclass(frozen=True)
class ExRightReport:
    stat: str                     # "OK", or TWSE's reason for having nothing to report
    results: List[ExRightResult]

    @property
    def found(self) -> bool:
        return self.stat == "OK"


def exright_results(client: TWSEAPIClient, start: date, end: date) -> ExRightReport:
    """Every listed ex-rights / ex-dividend result between ``start`` and ``end`` (inclusive)."""
    resp = client.fetch_json(
        TWT49U_URL,
        params={"startDate": f"{start:%Y%m%d}", "endDate": f"{end:%Y%m%d}", "response": "json"},
        cache_ttl=day_cache_ttl(f"{end:%Y%m%d}"),
    )
    if not isinstance(resp, dict):
        raise UpstreamFormatError(f"TWT49U 回應不是 JSON 物件：{str(resp)[:120]}")
    stat = str(resp.get("stat") or "無回應")
    if stat != "OK" or not resp.get("data"):
        return ExRightReport(stat=stat, results=[])
    col = column_index(resp.get("fields"), FIELDS, "TWT49U")
    results = []
    for r in resp["data"]:
        day = parse_roc_date(r[col["資料日期"]])
        if day is None:
            raise UpstreamFormatError(f"TWT49U 資料日期格式已變更：{r[col['資料日期']]!r}")
        results.append(ExRightResult(
            day=day,
            code=str(r[col["股票代號"]]).strip(),
            name=str(r[col["股票名稱"]]).strip(),
            close_before=decimal_or_none(r[col["除權息前收盤價"]]),
            reference=decimal_or_none(r[col["除權息參考價"]]),
            rights_and_dividend=decimal_or_none(r[col["權值+息值"]]),
            kind=str(r[col["權/息"]]).strip(),
            limit_up=decimal_or_none(r[col["漲停價格"]]),
            limit_down=decimal_or_none(r[col["跌停價格"]]),
            opening_reference=decimal_or_none(r[col["開盤競價基準"]]),
            ex_dividend_reference=decimal_or_none(r[col["減除股利參考價"]]),
            nav_per_share=str(r[col["最近一次申報每股 (單位)淨值"]]).strip(),
            eps=str(r[col["最近一次申報每股 (單位)盈餘"]]).strip(),
        ))
    return ExRightReport(stat=stat, results=results)
