"""Daily price series for one stock (listed or OTC) with optional ex-rights adjustment.

Sources, one request per calendar month:
- listed (TWSE): exchangeReport/STOCK_DAY — volume in shares
- OTC (TPEx):    www/zh-tw/afterTrading/tradingStock — volume in lots (張), converted to shares
Ex-rights/dividend results (one request for the whole span):
- listed: rwd/zh/exRight/TWT49U   - OTC: www/zh-tw/bulletin/exDailyQ
Both give 除權息前收盤價 and 除權息參考價; the ratio reference/close-before is the factor by
which every earlier price is multiplied for a backward-adjusted (還原權息) series.
"""

from dataclasses import dataclass, replace
from datetime import date
from typing import List, Optional, Tuple

from utils.api_client import TWSEAPIClient
from utils.date_helper import parse_roc_date, taipei_today
from sources.caching import PAST_MONTH_CACHE_TTL, month_cache_ttl
from sources.twse.stock_day import stock_day_month

TPEX_TRADING_STOCK_URL = "https://www.tpex.org.tw/www/zh-tw/afterTrading/tradingStock"
TWT49U_URL = "https://www.twse.com.tw/rwd/zh/exRight/TWT49U"
TPEX_EXRIGHT_URL = "https://www.tpex.org.tw/www/zh-tw/bulletin/exDailyQ"

LISTED, OTC = "上市", "上櫃"


@dataclass(frozen=True)
class Bar:
    day: date
    open: Optional[float]
    high: Optional[float]
    low: Optional[float]
    close: Optional[float]
    volume: float  # shares


@dataclass(frozen=True)
class ExRightEvent:
    day: date
    close_before: float
    reference: float
    kind: str  # 除權 / 除息 / 權息

    @property
    def factor(self) -> float:
        return self.reference / self.close_before


def _num(value) -> Optional[float]:
    text = str(value).replace(",", "").strip()
    try:
        return float(text)
    except ValueError:
        return None  # "--" on days without trades


def months_back(count: int, end: Optional[date] = None) -> List[Tuple[int, int]]:
    """The last ``count`` calendar months up to ``end`` (default: this month), oldest first."""
    end = end or taipei_today().date()
    y, m = end.year, end.month
    out = []
    for _ in range(count):
        out.append((y, m))
        y, m = (y - 1, 12) if m == 1 else (y, m - 1)
    return out[::-1]


def _float(value) -> Optional[float]:
    return None if value is None else float(value)


def _listed_month(client: TWSEAPIClient, code: str, y: int, m: int) -> Tuple[Optional[str], List[Bar]]:
    month = stock_day_month(client, code, y, m)
    if month is None:
        return None, []
    bars = [Bar(r.day, _float(r.open), _float(r.high), _float(r.low), _float(r.close), float(r.volume or 0))
            for r in month.rows]
    return month.name, bars


def _otc_month(client: TWSEAPIClient, code: str, y: int, m: int) -> Tuple[Optional[str], List[Bar]]:
    resp = client.fetch_json(
        TPEX_TRADING_STOCK_URL, params={"code": code, "date": f"{y}/{m:02d}/01", "response": "json"},
        cache_ttl=month_cache_ttl(y, m),
    )
    tables = (resp or {}).get("tables") or []
    rows = (tables[0].get("data") if tables else None) or []
    bars = []
    for r in rows:
        # r: 日期,成交張數,成交仟元,開盤,最高,最低,收盤,漲跌,筆數
        d = parse_roc_date(r[0])
        if d:
            bars.append(Bar(d, _num(r[3]), _num(r[4]), _num(r[5]), _num(r[6]), (_num(r[1]) or 0.0) * 1000))
    return (resp or {}).get("name") or None, bars


def fetch_daily_bars(client: TWSEAPIClient, code: str, months: List[Tuple[int, int]]) -> Tuple[Optional[str], str, List[Bar]]:
    """Daily bars for ``months`` (oldest first). Returns (market, name, bars) or (None, "", [])
    when the code trades on neither market in the most recent months requested.

    The market is detected from the newest month that has trades: listed first, then OTC.
    """
    market, name = None, ""
    fetched = {}
    for y, m in reversed(months):
        for mk, fetch in ((LISTED, _listed_month), (OTC, _otc_month)):
            nm, bars = fetch(client, code, y, m)
            if bars:
                market, name = mk, nm or ""
                fetched[(y, m)] = bars
                break
        if market:
            break
    if not market:
        return None, "", []
    fetch = _listed_month if market == LISTED else _otc_month
    bars: List[Bar] = []
    for y, m in months:
        bars += fetched.get((y, m)) or fetch(client, code, y, m)[1]
    return market, name, sorted(bars, key=lambda b: b.day)


def fetch_exright_events(client: TWSEAPIClient, market: str, code: str, start: date, end: date) -> List[ExRightEvent]:
    """Ex-rights / ex-dividend results for ``code`` between ``start`` and ``end``."""
    if market == LISTED:
        resp = client.fetch_json(
            TWT49U_URL, params={"startDate": f"{start:%Y%m%d}", "endDate": f"{end:%Y%m%d}", "response": "json"},
            cache_ttl=PAST_MONTH_CACHE_TTL,
        )
        rows = (resp or {}).get("data") or [] if (resp or {}).get("stat") == "OK" else []
    else:
        resp = client.fetch_json(
            TPEX_EXRIGHT_URL,
            params={"startDate": f"{start:%Y/%m/%d}", "endDate": f"{end:%Y/%m/%d}", "response": "json"},
            cache_ttl=PAST_MONTH_CACHE_TTL,
        )
        tables = (resp or {}).get("tables") or []
        rows = (tables[0].get("data") if tables else None) or []
    events = []
    for r in rows:
        # listed: 資料日期,股票代號,股票名稱,除權息前收盤價,除權息參考價,權值+息值,權/息, ...
        # OTC:    除權息日期,代號,名稱,除權息前收盤價,除權息參考價,權值,息值,權值+息值,權/息, ...
        if r[1].strip() != code:
            continue
        d, before, ref = parse_roc_date(r[0]), _num(r[3]), _num(r[4])
        if d and before and ref:
            kind = r[6] if market == LISTED else r[8]
            events.append(ExRightEvent(d, before, ref, str(kind).strip()))
    return sorted(events, key=lambda e: e.day)


def adjust_bars(bars: List[Bar], events: List[ExRightEvent]) -> List[Bar]:
    """Backward-adjust prices: each bar before an ex-date is multiplied by that event's factor."""
    out = []
    for b in bars:
        factor = 1.0
        for e in events:
            if b.day < e.day:
                factor *= e.factor
        if factor == 1.0:
            out.append(b)
            continue
        scale = lambda v: None if v is None else round(v * factor, 4)  # noqa: E731
        out.append(replace(b, open=scale(b.open), high=scale(b.high), low=scale(b.low), close=scale(b.close)))
    return out
