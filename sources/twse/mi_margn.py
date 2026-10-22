"""MI_MARGN: 融資融券彙總 — the market's credit-trading totals and every listed security's margin balances on one day.

``GET https://www.twse.com.tw/exchangeReport/MI_MARGN?response=json&selectType=ALL&date=20250103`` (no ``date`` = the
latest trading day). Reply::

    {"stat": "OK", "date": "20250103", "tables": [
      {"title": "114年01月03日 信用交易統計", "fields": ["項目", "買進", "賣出", "現金(券)償還", "前日餘額", "今日餘額"],
       "data": [["融資(交易單位)", "209,142", "218,874", "4,722", "8,738,199", "8,723,745"],
                ["融券(交易單位)", ...], ["融資金額(仟元)", ...]]},
      {"title": "114年01月03日 融資融券彙總 (全部)",
       "groups": [{"title": "股票", "span": 2}, {"title": "融資", "span": 6}, {"title": "融券", "span": 6},
                  {"title": "", "span": 1}, {"title": "", "span": 1}],
       "fields": ["代號", "名稱", "買進", "賣出", "現金償還", "前日餘額", "今日餘額", "次一營業日限額",
                  "買進", "賣出", "現券償還", "前日餘額", "今日餘額", "次一營業日限額", "資券互抵", "註記"],
       "data": [["0050", "元大台灣50", "22", "41", "0", "929", "910", "554,750", "5", "11", "0", "211", "217",
                 "554,750", "0", " "], ...]}]}

融資 and 融券 repeat their field names, so detail columns are found by group and name ("融券/今日餘額"); the tables
are found by their fields. 註記 is padded ("OX ", " ") and kept as published. A day without trading answers another
``stat``. Same layout checked 2005–2026.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from utils.api_client import TWSEAPIClient
from utils.errors import UpstreamFormatError
from utils.parse import int_or_none

from ..caching import day_cache_ttl
from ..columns import column_index, qualified_fields

MI_MARGN_URL = "https://www.twse.com.tw/exchangeReport/MI_MARGN"
SOURCE = "MI_MARGN"
SUMMARY_FIELDS = ("項目", "買進", "賣出", "現金(券)償還", "前日餘額", "今日餘額")
DETAIL_FIELDS = ("股票/代號", "股票/名稱",
                 "融資/買進", "融資/賣出", "融資/現金償還", "融資/前日餘額", "融資/今日餘額", "融資/次一營業日限額",
                 "融券/買進", "融券/賣出", "融券/現券償還", "融券/前日餘額", "融券/今日餘額", "融券/次一營業日限額",
                 "資券互抵", "註記")


@dataclass(frozen=True)
class CreditTotal:
    """One row of 信用交易統計."""
    item: str                  # 融資(交易單位) / 融券(交易單位) / 融資金額(仟元)
    buy: Optional[int]
    sell: Optional[int]
    repaid: Optional[int]      # 現金(券)償還
    previous: Optional[int]    # 前日餘額
    today: Optional[int]       # 今日餘額


@dataclass(frozen=True)
class CreditSide:
    """融資 or 融券 of one security, in 交易單位 (lots)."""
    buy: Optional[int]
    sell: Optional[int]
    repaid: Optional[int]          # 現金償還 (融資) / 現券償還 (融券)
    previous: Optional[int]        # 前日餘額
    today: Optional[int]           # 今日餘額
    next_day_limit: Optional[int]  # 次一營業日限額


@dataclass(frozen=True)
class MarginBalance:
    code: str
    name: str
    margin: CreditSide             # 融資
    short: CreditSide              # 融券
    offset: Optional[int]          # 資券互抵
    note: str                      # 註記 as published, padded: "OX ", "X ", " "


@dataclass(frozen=True)
class MarginDay:
    date: str                      # YYYYMMDD TWSE served
    totals: List[CreditTotal]      # 信用交易統計
    balances: List[MarginBalance]  # empty when the day has no detail rows


def _fields(table: Dict[str, Any]) -> List[str]:
    return [str(f).strip() for f in table.get("fields") or []]


def _side(r: List[Any], col: Dict[str, int], group: str, repaid: str) -> CreditSide:
    def n(name: str) -> Optional[int]:
        return int_or_none(r[col[f"{group}/{name}"]])
    return CreditSide(n("買進"), n("賣出"), n(repaid), n("前日餘額"), n("今日餘額"), n("次一營業日限額"))


def margin_balances(client: TWSEAPIClient, date: str = "") -> Optional[MarginDay]:
    """Credit-trading totals and every listed security's margin balances on ``date`` (YYYYMMDD; "" = latest
    trading day), or None when TWSE has none for that day. Raises ``UpstreamFormatError`` if the tables changed."""
    params = {"response": "json", "selectType": "ALL"}
    if date:
        params["date"] = date
    resp = client.fetch_json(MI_MARGN_URL, params=params, cache_ttl=day_cache_ttl(date))
    if not isinstance(resp, dict):
        raise UpstreamFormatError(f"{SOURCE} 回應不是 JSON 物件：{str(resp)[:120]}")
    if resp.get("stat") != "OK":
        return None
    served = str(resp.get("date") or date)
    tables = [t for t in resp.get("tables") or [] if isinstance(t, dict)]

    totals = []
    summary = next((t for t in tables if "項目" in _fields(t)), None)
    if summary is not None:
        col = column_index(_fields(summary), SUMMARY_FIELDS, SOURCE)
        for r in summary.get("data") or []:
            if len(r) != len(_fields(summary)):
                raise UpstreamFormatError(f"{SOURCE} 信用交易統計列有 {len(r)} 欄：{r}")
            totals.append(CreditTotal(
                item=str(r[col["項目"]]).strip(),
                buy=int_or_none(r[col["買進"]]),
                sell=int_or_none(r[col["賣出"]]),
                repaid=int_or_none(r[col["現金(券)償還"]]),
                previous=int_or_none(r[col["前日餘額"]]),
                today=int_or_none(r[col["今日餘額"]]),
            ))

    detail = next((t for t in tables if "代號" in _fields(t)), None)
    if detail is None:
        if any(t.get("data") for t in tables if t is not summary):
            raise UpstreamFormatError(f"{SOURCE} 找不到個股明細表（有「代號」欄位的表）：{[_fields(t) for t in tables]}")
        return MarginDay(date=served, totals=totals, balances=[])
    names = qualified_fields(_fields(detail), list(detail.get("groups") or []), SOURCE)
    col = column_index(names, DETAIL_FIELDS, SOURCE)
    balances = []
    for r in detail.get("data") or []:
        if len(r) != len(names):
            raise UpstreamFormatError(f"{SOURCE} 資料列有 {len(r)} 欄，欄位有 {len(names)} 個：{r}")
        balances.append(MarginBalance(
            code=str(r[col["股票/代號"]]).strip(),
            name=str(r[col["股票/名稱"]]).strip(),
            margin=_side(r, col, "融資", "現金償還"),
            short=_side(r, col, "融券", "現券償還"),
            offset=int_or_none(r[col["資券互抵"]]),
            note=str(r[col["註記"]]),
        ))
    return MarginDay(date=served, totals=totals, balances=balances)
