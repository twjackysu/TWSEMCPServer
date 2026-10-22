"""TPEx margin/balance: 上櫃股票融資融券餘額 — every OTC security's margin and short balances on one day, in lots.

``GET https://www.tpex.org.tw/www/zh-tw/margin/balance?date=2025/01/03&response=json`` (no ``date`` = the latest
day; 2005-01-03 has no rows, 2010-01-04 has). Reply::

    {"stat": "ok", "date": "20250103", "tables": [{"title": "上櫃股票融資融券餘額",
      "fields": ["代號", "名稱", "前資餘額(張)", "資買", "資賣", "現償", "資餘額", "資屬證金", "資使用率(%)", "資限額",
                 "前券餘額(張)", "券賣", "券買", "券償", "券餘額", "券屬證金", "券使用率(%)", "券限額", "資券相抵(張)", "備註"],
      "data": [["00679B", "元大美債20年", "28,292", "63", "445", "14", "27,896", "235", "1.04", "2,658,048",
                "2", "0", "1", "0", "1", "0", "0.0", "2,658,048", "2", ""], ...],
      "summary": [["", "合計(張)", "2,474,629", ..., "94,884", "", "", "", "", ""],
                  ["", "融資金(仟元)", "117,038,761", ..., "", "", ""]]}]}

The market totals sit in ``summary`` with the same fields, labelled in 名稱; the 融資金(仟元) row leaves the 券 columns
empty. Codes were padded on 2014 dates ("1259  "); 備註 holds flags such as "OX", "11     C". A day without trading has
no rows. Same fields checked 2010–2026.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, List, Optional

from utils.api_client import TWSEAPIClient
from utils.date_helper import slash_date
from utils.errors import UpstreamFormatError
from utils.parse import decimal_or_none, int_or_none

from ..caching import day_cache_ttl
from ..columns import column_index

MARGIN_BALANCE_URL = "https://www.tpex.org.tw/www/zh-tw/margin/balance"
SOURCE = "margin/balance"
FIELDS = ("代號", "名稱", "前資餘額(張)", "資買", "資賣", "現償", "資餘額", "資屬證金", "資使用率(%)", "資限額",
          "前券餘額(張)", "券賣", "券買", "券償", "券餘額", "券屬證金", "券使用率(%)", "券限額", "資券相抵(張)", "備註")


@dataclass(frozen=True)
class OtcCreditSide:
    """融資 or 融券 of one security, in lots."""
    previous: Optional[int]     # 前資餘額 / 前券餘額
    buy: Optional[int]          # 資買 / 券買
    sell: Optional[int]         # 資賣 / 券賣
    repaid: Optional[int]       # 現償 / 券償
    balance: Optional[int]      # 資餘額 / 券餘額
    finance: Optional[int]      # 資屬證金 / 券屬證金
    usage: Optional[Decimal]    # 資使用率 / 券使用率 (%)
    limit: Optional[int]        # 資限額 / 券限額


@dataclass(frozen=True)
class OtcMarginBalance:
    code: str
    name: str
    margin: OtcCreditSide       # 融資
    short: OtcCreditSide        # 融券
    offset: Optional[int]       # 資券相抵(張)
    note: str                   # 備註 flags as published ("OX", "11     C", "")


@dataclass(frozen=True)
class OtcMarginTotal:
    label: str                  # 合計(張) / 融資金(仟元)
    margin_balance: Optional[int]  # 資餘額
    short_balance: Optional[int]   # 券餘額; None on the 融資金(仟元) row


@dataclass(frozen=True)
class OtcMarginDay:
    date: str                   # the day TPEx answered for, YYYYMMDD
    balances: List[OtcMarginBalance]  # empty on a day without trading
    totals: List[OtcMarginTotal]


def _side(r: List, col: Dict[str, int], previous: str, buy: str, sell: str, repaid: str, balance: str,
          finance: str, usage: str, limit: str) -> OtcCreditSide:
    return OtcCreditSide(
        previous=int_or_none(r[col[previous]]), buy=int_or_none(r[col[buy]]), sell=int_or_none(r[col[sell]]),
        repaid=int_or_none(r[col[repaid]]), balance=int_or_none(r[col[balance]]),
        finance=int_or_none(r[col[finance]]), usage=decimal_or_none(r[col[usage]]), limit=int_or_none(r[col[limit]]),
    )


def otc_margin_balances(client: TWSEAPIClient, date: str = "") -> OtcMarginDay:
    """Every OTC security's margin and short balances on ``date`` (YYYYMMDD; "" = latest day), with the market
    totals. Raises ``UpstreamFormatError`` if the reply's shape or columns changed."""
    params = {"response": "json"}
    if date:
        params["date"] = slash_date(date)
    resp = client.fetch_json(MARGIN_BALANCE_URL, params=params, cache_ttl=day_cache_ttl(date))
    tables = resp.get("tables") if isinstance(resp, dict) else None
    if not isinstance(resp, dict) or not isinstance(tables, list):
        raise UpstreamFormatError(f"{SOURCE} 回應不再有 tables：{str(resp)[:120]}")
    served = str(resp.get("date") or "")
    table = tables[0] if tables and isinstance(tables[0], dict) else {}
    data = table.get("data") or []
    if not data:
        return OtcMarginDay(date=served, balances=[], totals=[])
    fields = [str(f).strip() for f in table.get("fields") or []]
    col = column_index(fields, FIELDS, SOURCE)
    rows = list(data) + list(table.get("summary") or [])
    for r in rows:
        if len(r) != len(fields):
            raise UpstreamFormatError(f"{SOURCE} 資料列有 {len(r)} 欄，欄位有 {len(fields)} 個：{r}")
    balances = [OtcMarginBalance(
        code=str(r[col["代號"]]).strip(),
        name=str(r[col["名稱"]]).strip(),
        margin=_side(r, col, "前資餘額(張)", "資買", "資賣", "現償", "資餘額", "資屬證金", "資使用率(%)", "資限額"),
        short=_side(r, col, "前券餘額(張)", "券買", "券賣", "券償", "券餘額", "券屬證金", "券使用率(%)", "券限額"),
        offset=int_or_none(r[col["資券相抵(張)"]]),
        note=str(r[col["備註"]]).strip(),
    ) for r in data]
    totals = [OtcMarginTotal(
        label=str(s[col["名稱"]]).strip(),
        margin_balance=int_or_none(s[col["資餘額"]]),
        short_balance=int_or_none(s[col["券餘額"]]),
    ) for s in table.get("summary") or []]
    return OtcMarginDay(date=served, balances=balances, totals=totals)
