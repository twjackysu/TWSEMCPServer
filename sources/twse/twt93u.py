"""TWT93U: 信用額度總量管制餘額表 — each listed security's short-sale (融券) and securities-lending sale
(借券賣出) balances on one day, in shares.

``GET https://www.twse.com.tw/rwd/zh/marginTrading/TWT93U?response=json&date=20250103&selectType=ALL``
(data from 2005-07-01). Reply::

    {"stat": "OK", "date": "20250103", "title": "114年01月03日 信用額度總量管制餘額表",
     "fields": ["代號", "名稱", "前日餘額", "賣出", "買進", "現券", "今日餘額", "次一營業日限額",
                "前日餘額", "當日賣出", "當日還券", "當日調整", "當日餘額", "次一營業日可限額", "備註"],
     "groups": [{"title": "股票", "span": 2}, {"title": "融券", "span": 6}, {"title": "借券賣出", "span": 6},
                {"title": "", "span": 1}],
     "data": [["0050", "元大台灣50", "211,000", "11,000", "5,000", "0", "217,000", "554,750,000", "21,992,000",
               "0", "99,000", "0", "21,893,000", "2,682,623", " "], ..., ["", "合計", ...]]}

Both groups have a 前日餘額, so a column is found by group and name ("借券賣出/前日餘額"). The 借券賣出
group changed on 2012-03-19, when TWSE started its new lending-balance formula: until 2012-03-16 it is
前日餘額, 賣出, 庫存異動 (= 履約 + 還券, signed), 今日餘額, 可使用額度 — five columns, so reading the new
layout by position put 可使用額度 under 當日餘額. The two layouts' figures are not the same quantities,
so each keeps its own fields. From 2014 a 合計 row closes the data; it is left out.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional

from utils.api_client import TWSEAPIClient
from utils.constants import SUMMARY_ROW_LABELS
from utils.errors import UpstreamFormatError
from utils.parse import int_or_none

from ..caching import day_cache_ttl
from ..columns import column_index

TWT93U_URL = "https://www.twse.com.tw/rwd/zh/marginTrading/TWT93U"
SOURCE = "TWT93U"
SHORT, LENDING = "融券", "借券賣出"
FIELDS = ("股票/代號", "股票/名稱", "融券/前日餘額", "融券/賣出", "融券/買進", "融券/現券", "融券/今日餘額",
          "融券/次一營業日限額", "借券賣出/前日餘額", "備註")
# 借券賣出 from 2012-03-19 / until 2012-03-16
LENDING_FIELDS = ("借券賣出/當日賣出", "借券賣出/當日還券", "借券賣出/當日調整", "借券賣出/當日餘額", "借券賣出/次一營業日可限額")
OLD_LENDING_FIELDS = ("借券賣出/賣出", "借券賣出/庫存異動", "借券賣出/今日餘額", "借券賣出/可使用額度")


@dataclass(frozen=True)
class ShortSale:
    """融券: today = previous + sold - bought - cash_returned."""
    previous: Optional[int]        # 前日餘額
    sold: Optional[int]            # 賣出
    bought: Optional[int]          # 買進
    cash_returned: Optional[int]   # 現券
    today: Optional[int]           # 今日餘額
    next_day_limit: Optional[int]  # 次一營業日限額


@dataclass(frozen=True)
class LendingSale:
    """借券賣出. From 2012-03-19 today = previous + sold - returned + adjusted, and the old-layout fields
    are None; until 2012-03-16 today = previous + sold + inventory_change, and the new-layout ones are."""
    previous: Optional[int]                   # 前日餘額
    sold: Optional[int]                       # 當日賣出 / 賣出
    today: Optional[int]                      # 當日餘額 / 今日餘額
    returned: Optional[int] = None            # 當日還券
    adjusted: Optional[int] = None            # 當日調整
    next_day_limit: Optional[int] = None      # 次一營業日可限額
    inventory_change: Optional[int] = None    # 庫存異動 (until 2012-03-16)
    available: Optional[int] = None           # 可使用額度 (until 2012-03-16)

    @property
    def old_layout(self) -> bool:
        return self.returned is None and self.inventory_change is not None


@dataclass(frozen=True)
class ShortSaleLendingRow:
    code: str
    name: str
    short: ShortSale
    lending: LendingSale
    note: str  # 備註 symbols as published, stripped: "X", "XV", "" (X 停券, Y 無信用交易資格, Z 暫停借券賣出 …)


@dataclass(frozen=True)
class ShortSaleLendingDay:
    date: str   # YYYYMMDD
    title: str  # "114年01月03日 信用額度總量管制餘額表"
    rows: List[ShortSaleLendingRow]


def qualified_fields(fields: List[str], groups: List[Dict]) -> List[str]:
    """Each column's name prefixed with its group title ("融券/前日餘額"); untitled groups keep the bare name."""
    spans = [int(g.get("span") or 0) for g in groups]
    if sum(spans) != len(fields):
        raise UpstreamFormatError(f"{SOURCE} groups 與 fields 對不上：{groups} / {fields}")
    names, i = [], 0
    for g, span in zip(groups, spans, strict=True):
        title = str(g.get("title") or "").strip()
        names += [f"{title}/{str(f).strip()}" if title else str(f).strip() for f in fields[i:i + span]]
        i += span
    return names


def short_sale_lending_balances(client: TWSEAPIClient, date: str) -> Optional[ShortSaleLendingDay]:
    """Every listed security's 融券 and 借券賣出 balances on ``date`` (YYYYMMDD), or None when TWSE has none
    (not a trading day, before 2005-07-01). Raises ``UpstreamFormatError`` if the reply's columns changed."""
    resp = client.fetch_json(TWT93U_URL, params={"response": "json", "date": date, "selectType": "ALL"},
                             cache_ttl=day_cache_ttl(date))
    if not isinstance(resp, dict):
        raise UpstreamFormatError(f"{SOURCE} 回應不是 JSON 物件：{str(resp)[:120]}")
    if resp.get("stat") != "OK":
        return None
    title = str(resp.get("title") or "")
    data = resp.get("data") or []
    if not data:
        return ShortSaleLendingDay(date=str(resp.get("date") or date), title=title, rows=[])
    names = qualified_fields(list(resp.get("fields") or []), list(resp.get("groups") or []))
    old = "借券賣出/庫存異動" in names
    col = column_index(names, FIELDS + (OLD_LENDING_FIELDS if old else LENDING_FIELDS), SOURCE)

    rows = []
    for r in data:
        if len(r) != len(names):
            raise UpstreamFormatError(f"{SOURCE} 資料列有 {len(r)} 欄，欄位有 {len(names)} 個：{r}")
        if str(r[col["股票/名稱"]]).strip() in SUMMARY_ROW_LABELS:
            continue
        number = {name: int_or_none(r[i]) for name, i in col.items()}
        n = number.__getitem__
        short = ShortSale(n("融券/前日餘額"), n("融券/賣出"), n("融券/買進"), n("融券/現券"), n("融券/今日餘額"),
                          n("融券/次一營業日限額"))
        if old:
            lending = LendingSale(n("借券賣出/前日餘額"), n("借券賣出/賣出"), n("借券賣出/今日餘額"),
                                  inventory_change=n("借券賣出/庫存異動"), available=n("借券賣出/可使用額度"))
        else:
            lending = LendingSale(n("借券賣出/前日餘額"), n("借券賣出/當日賣出"), n("借券賣出/當日餘額"),
                                  returned=n("借券賣出/當日還券"), adjusted=n("借券賣出/當日調整"),
                                  next_day_limit=n("借券賣出/次一營業日可限額"))
        rows.append(ShortSaleLendingRow(code=str(r[col["股票/代號"]]).strip(), name=str(r[col["股票/名稱"]]).strip(),
                                        short=short, lending=lending, note=str(r[col["備註"]]).strip()))
    return ShortSaleLendingDay(date=str(resp.get("date") or date), title=title, rows=rows)
