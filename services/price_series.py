"""Daily price series for one stock (listed or OTC) with optional ex-rights adjustment.

Sources, one request per calendar month:
- listed (TWSE): exchangeReport/STOCK_DAY (sources/twse/stock_day.py) — volume in shares
- OTC (TPEx):    www/zh-tw/afterTrading/tradingStock (sources/tpex/trading_stock.py) — volume in lots (張),
  converted to shares
Ex-rights/dividend results (one request for the whole span):
- listed: rwd/zh/exRight/TWT49U (sources/twse/twt49u.py)
- OTC:    www/zh-tw/bulletin/exDailyQ (sources/tpex/ex_daily_q.py)
Both give 除權息前收盤價 and 除權息參考價 (``close_before``, ``reference``); the ratio reference/close-before
is the factor by which every earlier price is multiplied for a backward-adjusted (還原權息) series.
"""

from dataclasses import dataclass, replace
from datetime import date
from typing import List, Optional, Tuple

from utils.api_client import TWSEAPIClient
from utils.date_helper import taipei_today
from utils.parse import float_or_none
from sources.tpex.ex_daily_q import otc_exright_results
from sources.tpex.trading_stock import trading_stock_month
from sources.twse.stock_day import stock_day_month
from sources.twse.twt49u import exright_results

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


def months_back(count: int, end: Optional[date] = None) -> List[Tuple[int, int]]:
    """The last ``count`` calendar months up to ``end`` (default: this month), oldest first."""
    end = end or taipei_today().date()
    y, m = end.year, end.month
    out = []
    for _ in range(count):
        out.append((y, m))
        y, m = (y - 1, 12) if m == 1 else (y, m - 1)
    return out[::-1]


def _listed_month(client: TWSEAPIClient, code: str, y: int, m: int) -> Tuple[Optional[str], List[Bar]]:
    month = stock_day_month(client, code, y, m)
    if month is None:
        return None, []
    bars = [Bar(r.day, float_or_none(r.open), float_or_none(r.high), float_or_none(r.low), float_or_none(r.close), float(r.volume or 0))
            for r in month.rows]
    return month.name, bars


def _otc_month(client: TWSEAPIClient, code: str, y: int, m: int) -> Tuple[Optional[str], List[Bar]]:
    month = trading_stock_month(client, code, y, m)
    if month is None:
        return None, []
    bars = [Bar(r.day, float_or_none(r.open), float_or_none(r.high), float_or_none(r.low), float_or_none(r.close), float(r.lots or 0) * 1000)
            for r in month.rows]
    return month.name or None, bars


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
    results = (exright_results(client, start, end).results if market == LISTED
               else otc_exright_results(client, start, end).results)
    events = [ExRightEvent(r.day, float(r.close_before), float(r.reference), r.kind)
              for r in results if r.code == code and r.close_before and r.reference]
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
        out.append(replace(b, open=_scaled(b.open, factor), high=_scaled(b.high, factor),
                           low=_scaled(b.low, factor), close=_scaled(b.close, factor)))
    return out


def _scaled(price: Optional[float], factor: float) -> Optional[float]:
    return None if price is None else round(price * factor, 4)
