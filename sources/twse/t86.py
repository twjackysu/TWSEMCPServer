"""T86: 三大法人買賣超日報 — every listed security's institutional buying and selling (shares) on one day.

``GET https://www.twse.com.tw/rwd/zh/fund/T86?response=json&selectType=ALLBUT0999&date=20260930``
(no ``date`` = latest day; history from 2012-05-02). ``selectType``: ALL (~93% warrants / CBBCs),
ALLBUT0999 (no warrants), 0099P (ETFs) or a two-digit industry code. A day without data, an unknown
selectType or an unreadable date all come back as a ``stat`` other than "OK". Names are space-padded.

The columns changed twice; every layout is read by name:
- 12 fields (to 2014-11-28): 外資 / 投信 / 自營商, each 買進 / 賣出 / 買賣超
- 16 fields (2014-12-01 – 2017-12-15): 自營商 split into (自行買賣) and (避險); its total only as a net
- 19 fields (since 2017-12-18): 外資 split into 外陸資(不含外資自營商) and 外資自營商
"""

from typing import Callable, List, Optional

from utils.api_client import TWSEAPIClient
from utils.errors import UpstreamFormatError

from ..caching import day_cache_ttl
from ..columns import column_index
from ..institutional import FlowDay, InstitutionalFlow, Trades, shares

T86_URL = "https://www.twse.com.tw/rwd/zh/fund/T86"
SOURCE = "T86"


def _group(who: str, suffix: str = ""):
    return tuple(f"{who}{kind}股數{suffix}" for kind in ("買進", "賣出", "買賣超"))


FOREIGN = _group("外資")
FOREIGN_EX_DEALER = _group("外陸資", "(不含外資自營商)")
FOREIGN_DEALER = _group("外資自營商")
TRUST = _group("投信")
DEALER = _group("自營商")
DEALER_SELF = _group("自營商", "(自行買賣)")
DEALER_HEDGE = _group("自營商", "(避險)")
DEALER_NET = "自營商買賣超股數"
TOTAL_NET = "三大法人買賣超股數"


def t86_flows(client: TWSEAPIClient, select_type: str = "ALLBUT0999", date: str = "") -> Optional[FlowDay]:
    """Every security's 三大法人 flows on ``date`` (YYYYMMDD; "" = latest day); None when TWSE has none."""
    params = {"response": "json", "selectType": select_type}
    if date:
        params["date"] = date
    resp = client.fetch_json(T86_URL, params=params, cache_ttl=day_cache_ttl(date))
    if not isinstance(resp, dict):
        raise UpstreamFormatError(f"T86 回應不是 JSON 物件：{str(resp)[:120]}")
    if resp.get("stat") != "OK":
        return None
    rows = resp.get("data") or []
    parse = _row_parser(resp.get("fields")) if rows else None
    return FlowDay(date=str(resp.get("date") or ""), title=str(resp.get("title") or ""),
                   flows=[parse(r) for r in rows])


def _row_parser(published_fields) -> Callable[[List[str]], InstitutionalFlow]:
    """A reader for rows of whichever layout ``published_fields`` describes."""
    fields = [str(f).strip() for f in published_fields or []]
    split_foreign = FOREIGN_EX_DEALER[0] in fields
    split_dealer = DEALER_SELF[0] in fields
    groups = [TRUST]
    groups += [FOREIGN_EX_DEALER, FOREIGN_DEALER] if split_foreign else [FOREIGN]
    groups += [DEALER_SELF, DEALER_HEDGE] if split_dealer else [DEALER]
    col = column_index(fields, ["證券代號", "證券名稱", DEALER_NET, TOTAL_NET, *(n for g in groups for n in g)], SOURCE)

    def parse(r: List[str]) -> InstitutionalFlow:
        if len(r) != len(fields):
            raise UpstreamFormatError(f"T86 資料列有 {len(r)} 欄，欄位有 {len(fields)} 個：{r}")

        def trades(group) -> Trades:
            return Trades(*(shares(r[col[name]], SOURCE, name) for name in group))

        if split_foreign:
            ex_dealer, foreign_dealer = trades(FOREIGN_EX_DEALER), trades(FOREIGN_DEALER)
            foreign = Trades(ex_dealer.buy + foreign_dealer.buy, ex_dealer.sell + foreign_dealer.sell,
                             ex_dealer.net + foreign_dealer.net)
        else:
            ex_dealer = foreign_dealer = None
            foreign = trades(FOREIGN)
        if split_dealer:
            dealer_self, dealer_hedge = trades(DEALER_SELF), trades(DEALER_HEDGE)
            dealer = Trades(None, None, shares(r[col[DEALER_NET]], SOURCE, DEALER_NET))
        else:
            dealer_self = dealer_hedge = None
            dealer = trades(DEALER)
        return InstitutionalFlow(
            code=str(r[col["證券代號"]]).strip(),
            name=str(r[col["證券名稱"]]).strip(),
            foreign=foreign,
            foreign_ex_dealer=ex_dealer,
            foreign_dealer=foreign_dealer,
            trust=trades(TRUST),
            dealer=dealer,
            dealer_self=dealer_self,
            dealer_hedge=dealer_hedge,
            total_net=shares(r[col[TOTAL_NET]], SOURCE, TOTAL_NET),
        )

    return parse
