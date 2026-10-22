"""TPEx afterTrading/otc: 上櫃股票每日收盤行情（不含定價） — every OTC security's quotes on one day.

``GET https://www.tpex.org.tw/www/zh-tw/afterTrading/otc?date=2025/01/03&type=EW&response=json``
(no ``date`` = latest day; ``type``: EW stocks and ETFs, AL every security including ~10,700
warrants, or a two-digit industry code, whose table's ``category`` names the industry). Reply::

    {"date": "20250103", "stat": "ok",
     "tables": [{"title": "上櫃股票每日收盤行情(不含定價)", "category": "",
                 "fields": ["代號", "名稱", "收盤 ", "漲跌", "開盤 ", "最高 ", "最低", "成交股數  ", " 成交金額(元)",
                            " 成交筆數 ", "最後買價", "最後買量<br>(千股)", "最後賣價", "最後賣量<br>(千股)", "發行股數 ",
                            "次日漲停價 ", "次日跌停價"],
                 "data": [["00679B", "元大美債20年", "28.63", "+0.23", "28.56", "28.64", "28.54", "24,715,000",
                           "706,690,560", "3,325", "28.62", "5,480", "28.63", "222", "10,632,692,000", ...], ...]}]}

最後買量 / 最後賣量 only exist from 2020-04-30 (their unit label is 千股 or 張數 depending on the day): before
that 最後賣價 is the 12th column, not the 13th, so columns are found by name (with spaces and ``<br>``
removed). A day without trading is an empty table.
Prices without a trade are "----"; 漲跌 is "---", "除息" or "除權" on such days and was printed as
"- 0.19" (sign, space) in older years. Prices carry thousands separators from 2018 on, not before.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import List, Optional

from utils.api_client import TWSEAPIClient
from utils.date_helper import slash_date
from utils.errors import UpstreamFormatError
from utils.parse import decimal_or_none, int_or_none

from ..caching import day_cache_ttl
from ..columns import column_index

DAILY_QUOTES_URL = "https://www.tpex.org.tw/www/zh-tw/afterTrading/otc"
SOURCE = "afterTrading/otc"
# type: stocks and ETFs (~1,000 rows), or every security (~11,700 rows, ~1.5 MB); or an industry code
STOCKS_AND_ETFS, ALL_SECURITIES = "EW", "AL"
FIELDS = ("代號", "名稱", "收盤", "漲跌", "開盤", "最高", "最低", "成交股數", "成交金額(元)", "成交筆數", "最後買價", "最後賣價")


@dataclass(frozen=True)
class OtcQuote:
    code: str
    name: str
    close: Optional[Decimal]      # None when there was no trade ("----")
    change: str                   # 漲跌 exactly as published: "+0.23", "- 0.19", "---", "除息"
    open: Optional[Decimal]
    high: Optional[Decimal]
    low: Optional[Decimal]
    volume: Optional[int]         # 成交股數 (shares; 定價 trades not included)
    value: Optional[int]          # 成交金額 (NT$)
    transactions: Optional[int]   # 成交筆數
    last_bid: Optional[Decimal]   # 最後買價
    last_ask: Optional[Decimal]   # 最後賣價


@dataclass(frozen=True)
class OtcQuoteDay:
    date: str                     # the day TPEx answered for, YYYYMMDD
    group: str                    # the industry's name for an industry-code type, else ""
    quotes: List[OtcQuote]


def otc_daily_quotes(client: TWSEAPIClient, date: str = "", security_type: str = STOCKS_AND_ETFS) -> Optional[OtcQuoteDay]:
    """The quotes of ``security_type`` (EW, AL or an industry code) on ``date`` (YYYYMMDD; "" = latest day),
    or None when TPEx has none (not a trading day). Raises ``UpstreamFormatError`` if the reply's shape
    or columns changed."""
    params = {"type": security_type, "response": "json"}
    if date:
        params["date"] = slash_date(date)
    resp = client.fetch_json(DAILY_QUOTES_URL, params=params, cache_ttl=day_cache_ttl(date))
    tables = resp.get("tables") if isinstance(resp, dict) else None
    if not isinstance(resp, dict) or not isinstance(tables, list):
        raise UpstreamFormatError(f"{SOURCE} 回應不再有 tables：{str(resp)[:120]}")
    table = tables[0] if tables and isinstance(tables[0], dict) else {}
    data = table.get("data") or []
    if not data:
        return None
    fields = ["".join(str(f).replace("<br>", "").split()) for f in table.get("fields") or []]
    col = column_index(fields, FIELDS, SOURCE)
    quotes = []
    for r in data:
        if len(r) != len(fields):
            raise UpstreamFormatError(f"{SOURCE} 資料列有 {len(r)} 欄，欄位有 {len(fields)} 個：{r}")
        quotes.append(OtcQuote(
            code=str(r[col["代號"]]).strip(),
            name=str(r[col["名稱"]]).strip(),
            close=decimal_or_none(r[col["收盤"]]),
            change=str(r[col["漲跌"]]),
            open=decimal_or_none(r[col["開盤"]]),
            high=decimal_or_none(r[col["最高"]]),
            low=decimal_or_none(r[col["最低"]]),
            volume=int_or_none(r[col["成交股數"]]),
            value=int_or_none(r[col["成交金額(元)"]]),
            transactions=int_or_none(r[col["成交筆數"]]),
            last_bid=decimal_or_none(r[col["最後買價"]]),
            last_ask=decimal_or_none(r[col["最後賣價"]]),
        ))
    return OtcQuoteDay(date=str(resp.get("date") or ""), group=str(table.get("category") or ""), quotes=quotes)
