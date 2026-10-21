"""Latest-day whole-market snapshot (valuation + price) of listed and OTC stocks, and industry
membership, for screening and peer comparison.

Sources (latest trading day, each one request, cached):
- listed valuation:  TWSE rwd BWIBBU_d        (收盤價, 殖利率, 股利年度, 本益比, 股價淨值比, 財報年/季;
                     gateway: sources/twse/bwibbu_d.py)
- listed prices:     TWSE rwd MI_INDEX ALLBUT0999 每日收盤行情 (gateway: sources/twse/mi_index.py)
- OTC valuation:     TPEx afterTrading/peQryDate
- OTC prices:        TPEx afterTrading/otc type=EW
- industry of a stock: TWSE OpenAPI t187ap03_L 產業別 / TPEx OpenAPI mopsfin_t187ap03_O
  SecuritiesIndustryCode — both use the same two-digit codes (e.g. 24 = 半導體)
- industry members:  MI_INDEX type=<code> (its quote table's title names the industry) /
  afterTrading/otc type=<code>

The valuation endpoints publish a day later than the quote endpoints (on 2026-09-30 during
the evening both valuations still showed 09-29 while quotes showed 09-30), so prices are
fetched for the date the valuation actually served; mixing the two would pair one day's
close with the previous day's P/E.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from utils.api_client import TWSEAPIClient
from utils.date_helper import slash_date
from utils.parse import float_or_none
from sources.twse.bwibbu_d import valuation_ratios
from sources.twse.mi_index import stock_quotes

TPEX_PE_URL = "https://www.tpex.org.tw/www/zh-tw/afterTrading/peQryDate"
TPEX_QUOTES_URL = "https://www.tpex.org.tw/www/zh-tw/afterTrading/otc"
TPEX_PROFILE_URL = "https://www.tpex.org.tw/openapi/v1/mopsfin_t187ap03_O"
LISTED_PROFILE_ENDPOINT = "/opendata/t187ap03_L"

SNAPSHOT_CACHE_TTL = 600
LISTED, OTC = "上市", "上櫃"


@dataclass
class StockSnapshot:
    code: str
    name: str
    market: str
    close: Optional[float] = None
    change: Optional[float] = None
    pe: Optional[float] = None
    pb: Optional[float] = None
    dividend_yield: Optional[float] = None
    dividend_year: str = ""
    fiscal: str = ""
    volume: Optional[float] = None

    @property
    def change_pct(self) -> Optional[float]:
        if self.close is None or self.change is None or self.close == self.change:
            return None
        return self.change / (self.close - self.change) * 100


def _listed(client: TWSEAPIClient) -> Tuple[Dict[str, StockSnapshot], str]:
    out: Dict[str, StockSnapshot] = {}
    report = valuation_ratios(client)
    day = report.date
    for v in report.valuations:
        out[v.code] = StockSnapshot(v.code, v.name, LISTED, close=float_or_none(v.close), dividend_yield=float_or_none(v.dividend_yield),
                                    dividend_year=v.dividend_year, pe=float_or_none(v.pe), pb=float_or_none(v.pb), fiscal=v.fiscal)
    table = stock_quotes(client, "ALLBUT0999", day)
    for q in table.quotes if table else []:
        s = out.setdefault(q.code, StockSnapshot(q.code, q.name, LISTED))
        s.close = s.close if s.close is not None else float_or_none(q.close)
        if q.change is not None:
            s.change = float(q.change)
        s.volume = float_or_none(q.volume)
    return out, day


def _otc(client: TWSEAPIClient) -> Tuple[Dict[str, StockSnapshot], str]:
    out: Dict[str, StockSnapshot] = {}
    val = client.fetch_json(TPEX_PE_URL, params={"response": "json"}, cache_ttl=SNAPSHOT_CACHE_TTL)
    day = str((val or {}).get("date") or "")
    for r in ((val or {}).get("tables") or [{}])[0].get("data") or []:
        # r: 股票代號,公司名稱,本益比,每股股利,股利年度,殖利率(%),股價淨值比,財報年/季
        out[r[0].strip()] = StockSnapshot(r[0].strip(), r[1].strip(), OTC, pe=float_or_none(r[2]), dividend_year=str(r[4]),
                                          dividend_yield=float_or_none(r[5]), pb=float_or_none(r[6]), fiscal=str(r[7]))
    params = {"response": "json", "type": "EW"}
    if len(day) == 8:
        params["date"] = slash_date(day)
    quotes = client.fetch_json(TPEX_QUOTES_URL, params=params, cache_ttl=SNAPSHOT_CACHE_TTL)
    for r in ((quotes or {}).get("tables") or [{}])[0].get("data") or []:
        # r: 代號,名稱,收盤,漲跌(帶正負號),開盤,最高,最低,成交股數,...
        s = out.setdefault(r[0].strip(), StockSnapshot(r[0].strip(), r[1].strip(), OTC))
        s.close, s.change, s.volume = float_or_none(r[2]), float_or_none(r[3]), float_or_none(r[7])
    return out, day


def market_snapshot(client: TWSEAPIClient,
                    markets: Tuple[str, ...] = (LISTED, OTC)) -> Tuple[Dict[str, StockSnapshot], Dict[str, str]]:
    """(code → snapshot, market → data date YYYYMMDD or "") for the latest day with valuation data per market."""
    out: Dict[str, StockSnapshot] = {}
    days: Dict[str, str] = {}
    for market, loader in ((LISTED, _listed), (OTC, _otc)):
        if market in markets:
            rows, day = loader(client)
            out.update(rows)
            days[market] = day
    return out, days


def data_date_label(days: Dict[str, str]) -> str:
    """「上市 20261021、上櫃 20261021」: the data date of each market in a snapshot."""
    return "、".join(f"{market} {day or '?'}" for market, day in days.items())


def industry_of(client: TWSEAPIClient, code: str) -> Optional[str]:
    """Two-digit industry code of a listed or OTC company, or None."""
    listed = client.fetch_company_data(LISTED_PROFILE_ENDPOINT, code)
    if listed and listed.get("產業別"):
        return str(listed["產業別"]).strip()
    otc = client.fetch_json(TPEX_PROFILE_URL, cache_ttl=SNAPSHOT_CACHE_TTL)
    for r in otc if isinstance(otc, list) else []:
        if str(r.get("SecuritiesCompanyCode", "")).strip() == code:
            return str(r.get("SecuritiesIndustryCode", "")).strip() or None
    return None


def industry_members(client: TWSEAPIClient, industry: str) -> Tuple[str, List[str]]:
    """(industry name, codes of listed + OTC members) for a two-digit industry code."""
    name, codes = "", []
    listed = stock_quotes(client, industry)
    if listed:
        name, codes = listed.group, [q.code for q in listed.quotes]
    otc = client.fetch_json(TPEX_QUOTES_URL, params={"response": "json", "type": industry}, cache_ttl=SNAPSHOT_CACHE_TTL)
    table = ((otc or {}).get("tables") or [{}])[0]
    codes += [r[0].strip() for r in table.get("data") or []]
    name = name or str(table.get("category") or "")
    return name, codes
