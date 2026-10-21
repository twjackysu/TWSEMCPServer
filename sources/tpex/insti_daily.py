"""TPEx insti/dailyTrade: 三大法人買賣明細 — every OTC security's institutional buying and selling (shares).

``GET https://www.tpex.org.tw/www/zh-tw/insti/dailyTrade?type=Daily&sect=EW&date=2026/09/30&response=json``
(no ``date`` = latest day; data from 2018). ``sect``: EW (no warrants / CBBCs), EE (ETFs), AL (all) or
a two-digit industry code. A day without data, or an unknown ``sect``, comes back as an empty table.

``tables[0].fields`` is 代號, 名稱, then seven groups all headed 買進股數 / 賣出股數 / 買賣超股數, then
三大法人買賣超股數合計. The web page names the groups in a header row the JSON leaves out, so they can
only be told apart by order (``GROUPS``). Every row is checked against the sums that order implies
(外資合計 = 不含自營商 + 外資自營商, 自營商合計 = 自行 + 避險, 三大法人 = 外資 + 投信 + 自營商):
a reordering fails there instead of showing one group's numbers under another's name.
"""

from typing import Optional

from utils.api_client import TWSEAPIClient
from utils.date_helper import slash_date
from utils.errors import UpstreamFormatError

from ..caching import day_cache_ttl
from ..institutional import FlowDay, InstitutionalFlow, Trades, shares

INSTI_DAILY_URL = "https://www.tpex.org.tw/www/zh-tw/insti/dailyTrade"
SOURCE = "insti/dailyTrade"
GROUPS = ("foreign_ex_dealer", "foreign_dealer", "foreign", "trust", "dealer_self", "dealer_hedge", "dealer")
FIELDS = ["代號", "名稱"] + ["買進股數", "賣出股數", "買賣超股數"] * len(GROUPS) + ["三大法人買賣超股數合計"]


def tpex_flows(client: TWSEAPIClient, sect: str = "EW", date: str = "") -> Optional[FlowDay]:
    """Every OTC security's 三大法人 flows on ``date`` (YYYYMMDD; "" = latest day); None when TPEx has none."""
    params = {"type": "Daily", "sect": sect, "response": "json"}
    if date:
        params["date"] = slash_date(date)
    resp = client.fetch_json(INSTI_DAILY_URL, params=params, cache_ttl=day_cache_ttl(date))
    tables = resp.get("tables") if isinstance(resp, dict) else None
    if not isinstance(tables, list):
        raise UpstreamFormatError(f"{SOURCE} 回應不再有 tables：{str(resp)[:120]}")
    table = tables[0] if tables and isinstance(tables[0], dict) else {}
    rows = table.get("data") or []
    if not rows:
        return None
    fields = [str(f).strip() for f in table.get("fields") or []]
    if fields != FIELDS:
        raise UpstreamFormatError(f"{SOURCE} 欄位已變更：{fields}")
    return FlowDay(date=str(resp.get("date") or ""), title=str(table.get("subtitle") or table.get("title") or ""),
                   flows=[_flow(r) for r in rows])


def _flow(r) -> InstitutionalFlow:
    if len(r) != len(FIELDS):
        raise UpstreamFormatError(f"{SOURCE} 資料列有 {len(r)} 欄，應為 {len(FIELDS)}：{r}")
    numbers = [shares(value, SOURCE, FIELDS[i]) for i, value in enumerate(r[2:], start=2)]
    g = {name: Trades(*numbers[3 * i:3 * i + 3]) for i, name in enumerate(GROUPS)}
    total = numbers[-1]
    if (g["foreign"].net != g["foreign_ex_dealer"].net + g["foreign_dealer"].net
            or g["dealer"].net != g["dealer_self"].net + g["dealer_hedge"].net
            or total != g["foreign"].net + g["trust"].net + g["dealer"].net):
        raise UpstreamFormatError(f"{SOURCE} 欄位分組與買賣超加總不符，欄位順序可能已變更：{r}")
    return InstitutionalFlow(code=str(r[0]).strip(), name=str(r[1]).strip(), total_net=total, **g)
