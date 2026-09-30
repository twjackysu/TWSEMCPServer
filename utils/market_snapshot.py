"""Latest-day whole-market snapshot (valuation + price) of listed and OTC stocks, and industry
membership, for screening and peer comparison.

Sources (latest trading day, each one request, cached):
- listed valuation:  TWSE rwd BWIBBU_d        (收盤價, 殖利率, 股利年度, 本益比, 股價淨值比, 財報年/季)
- listed prices:     TWSE rwd MI_INDEX ALLBUT0999 每日收盤行情 (漲跌 sign + 漲跌價差, 成交股數)
- OTC valuation:     TPEx afterTrading/peQryDate
- OTC prices:        TPEx afterTrading/otc type=EW
- industry of a stock: TWSE OpenAPI t187ap03_L 產業別 / TPEx OpenAPI mopsfin_t187ap03_O
  SecuritiesIndustryCode — both use the same two-digit codes (e.g. 24 = 半導體)
- industry members:  MI_INDEX type=<code> / afterTrading/otc type=<code>, whose table titles
  also carry the industry name

The valuation endpoints publish a day later than the quote endpoints (on 2026-09-30 during
the evening both valuations still showed 09-29 while quotes showed 09-30), so prices are
fetched for the date the valuation actually served; mixing the two would pair one day's
close with the previous day's P/E.
"""

import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from .api_client import TWSEAPIClient

BWIBBU_D_URL = "https://www.twse.com.tw/rwd/zh/afterTrading/BWIBBU_d"
MI_INDEX_URL = "https://www.twse.com.tw/rwd/zh/afterTrading/MI_INDEX"
TPEX_PE_URL = "https://www.tpex.org.tw/www/zh-tw/afterTrading/peQryDate"
TPEX_QUOTES_URL = "https://www.tpex.org.tw/www/zh-tw/afterTrading/otc"
TPEX_PROFILE_URL = "https://www.tpex.org.tw/openapi/v1/mopsfin_t187ap03_O"
LISTED_PROFILE_ENDPOINT = "/opendata/t187ap03_L"

SNAPSHOT_CACHE_TTL = 600
LISTED, OTC = "上市", "上櫃"
_TAG_RE = re.compile(r"<[^>]+>")


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


def _num(value) -> Optional[float]:
    text = str(value).replace(",", "").replace("%", "").strip()
    try:
        return float(text)
    except ValueError:
        return None  # "-", "--", "N/A": no value (e.g. P/E of a loss-making company)


def _listed(client: TWSEAPIClient) -> Tuple[Dict[str, StockSnapshot], str]:
    out: Dict[str, StockSnapshot] = {}
    val = client.fetch_json(BWIBBU_D_URL, params={"response": "json", "selectType": "ALL"}, cache_ttl=SNAPSHOT_CACHE_TTL)
    day = str((val or {}).get("date") or "")
    for r in (val or {}).get("data") or []:
        # r: 證券代號,證券名稱,收盤價,殖利率(%),股利年度,本益比,股價淨值比,財報年/季
        out[r[0].strip()] = StockSnapshot(r[0].strip(), r[1].strip(), LISTED, close=_num(r[2]),
                                          dividend_yield=_num(r[3]), dividend_year=str(r[4]), pe=_num(r[5]),
                                          pb=_num(r[6]), fiscal=str(r[7]))
    params = {"response": "json", "type": "ALLBUT0999"}
    if day:
        params["date"] = day
    quotes = client.fetch_json(MI_INDEX_URL, params=params, cache_ttl=SNAPSHOT_CACHE_TTL)
    table = next((t for t in (quotes or {}).get("tables") or [] if "每日收盤行情" in (t.get("title") or "")), {})
    for r in table.get("data") or []:
        # r: 代號,名稱,成交股數,成交筆數,成交金額,開,高,低,收,漲跌(+/-)(HTML),漲跌價差,...
        s = out.setdefault(r[0].strip(), StockSnapshot(r[0].strip(), r[1].strip(), LISTED))
        s.close = s.close if s.close is not None else _num(r[8])
        change = _num(r[10])
        if change is not None:
            s.change = -change if _TAG_RE.sub("", str(r[9])).strip() == "-" else change
        s.volume = _num(r[2])
    return out, day


def _otc(client: TWSEAPIClient) -> Tuple[Dict[str, StockSnapshot], str]:
    out: Dict[str, StockSnapshot] = {}
    val = client.fetch_json(TPEX_PE_URL, params={"response": "json"}, cache_ttl=SNAPSHOT_CACHE_TTL)
    day = str((val or {}).get("date") or "")
    for r in ((val or {}).get("tables") or [{}])[0].get("data") or []:
        # r: 股票代號,公司名稱,本益比,每股股利,股利年度,殖利率(%),股價淨值比,財報年/季
        out[r[0].strip()] = StockSnapshot(r[0].strip(), r[1].strip(), OTC, pe=_num(r[2]), dividend_year=str(r[4]),
                                          dividend_yield=_num(r[5]), pb=_num(r[6]), fiscal=str(r[7]))
    params = {"response": "json", "type": "EW"}
    if len(day) == 8:
        params["date"] = f"{day[:4]}/{day[4:6]}/{day[6:]}"
    quotes = client.fetch_json(TPEX_QUOTES_URL, params=params, cache_ttl=SNAPSHOT_CACHE_TTL)
    for r in ((quotes or {}).get("tables") or [{}])[0].get("data") or []:
        # r: 代號,名稱,收盤,漲跌(帶正負號),開盤,最高,最低,成交股數,...
        s = out.setdefault(r[0].strip(), StockSnapshot(r[0].strip(), r[1].strip(), OTC))
        s.close, s.change, s.volume = _num(r[2]), _num(r[3]), _num(r[7])
    return out, day


def market_snapshot(client: TWSEAPIClient, markets: Tuple[str, ...] = (LISTED, OTC)) -> Tuple[Dict[str, StockSnapshot], str]:
    """(code → snapshot, data-date label) for the latest day with valuation data per market."""
    out: Dict[str, StockSnapshot] = {}
    days = []
    for market, loader in ((LISTED, _listed), (OTC, _otc)):
        if market in markets:
            rows, day = loader(client)
            out.update(rows)
            days.append(f"{market} {day or '?'}")
    return out, "、".join(days)


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
    quotes = client.fetch_json(MI_INDEX_URL, params={"response": "json", "type": industry}, cache_ttl=SNAPSHOT_CACHE_TTL)
    for t in (quotes or {}).get("tables") or []:
        title = t.get("title") or ""
        m = re.search(r"每日收盤行情\((.+?)\)", title)
        if m:
            name = m.group(1)
            codes += [r[0].strip() for r in t.get("data") or []]
    otc = client.fetch_json(TPEX_QUOTES_URL, params={"response": "json", "type": industry}, cache_ttl=SNAPSHOT_CACHE_TTL)
    table = ((otc or {}).get("tables") or [{}])[0]
    codes += [r[0].strip() for r in table.get("data") or []]
    name = name or str(table.get("category") or "")
    return name, codes
