"""futDataDown / optDataDown: 期貨 / 選擇權每日交易行情 — each contract month's (and option strike's) daily quote.

``POST https://www.taifex.com.tw/cht/3/futDataDown`` with ``down_type=1``, ``commodity_id=TX`` (or
``all``), ``commodity_id2=""`` and the date range (about a month at most). Reply (cp950 CSV)::

    交易日期,契約,到期月份(週別),開盤價,最高價,最低價,收盤價,漲跌價,漲跌%,成交量,結算價,未沖銷契約數,最後最佳買價,
    最後最佳賣價,歷史最高價,歷史最低價,是否因訊息面暫停交易,交易時段,價差對單式委託成交量
    2025/01/03,TX,202501  ,22935,23108,22905,22977,134,0.59%,62488,22977,71366,22976,22980,23996,22039,,一般,,

optDataDown adds 履約價 ("20500.0000") and 買賣權 (買權 / 賣權) after 到期月份 and moves 漲跌價 / 漲跌% to the end; from
2026 it also has 契約到期日. Every row is one session: 一般 (regular) or 盤後 (after-hours, dated the evening it
started). 到期月份 is padded with spaces; a calendar spread is "202501/202502". Columns are found by name; same
layout checked 2005–2026.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import List, Optional, Sequence, Union

from utils.api_client import TWSEAPIClient
from utils.taifex import TAIFEX_DOWNLOAD_BASE

from .download import count, download_table, number, trade_date

FUT_DATA_DOWN_URL = f"{TAIFEX_DOWNLOAD_BASE}/futDataDown"
OPT_DATA_DOWN_URL = f"{TAIFEX_DOWNLOAD_BASE}/optDataDown"
ALL_CONTRACTS = "all"  # commodity_id for every contract
REGULAR_SESSION = "一般"
QUOTE_FIELDS = ("交易日期", "契約", "到期月份(週別)", "開盤價", "最高價", "最低價", "收盤價", "成交量", "結算價",
                "未沖銷契約數", "最後最佳買價", "最後最佳賣價", "交易時段")
FUTURES_FIELDS = QUOTE_FIELDS + ("漲跌價", "漲跌%")
OPTIONS_FIELDS = QUOTE_FIELDS + ("履約價", "買賣權")


@dataclass(frozen=True)
class FuturesQuote:
    day: date
    contract: str                  # 契約: TX, MTX, CDF …
    month: str                     # 到期月份(週別): "202501", "202501W2", spread "202501/202502"
    open: Optional[Decimal]        # None where TAIFEX prints "-" (no trade)
    high: Optional[Decimal]
    low: Optional[Decimal]
    close: Optional[Decimal]
    change: Optional[Decimal]      # 漲跌價
    change_pct: str                # 漲跌% as published: "0.59%", "-"
    volume: Optional[int]          # 成交量 (contracts)
    settlement: Optional[Decimal]  # 結算價
    open_interest: Optional[int]   # 未沖銷契約數
    best_bid: Optional[Decimal]    # 最後最佳買價
    best_ask: Optional[Decimal]    # 最後最佳賣價
    session: str                   # 交易時段: 一般 / 盤後


@dataclass(frozen=True)
class OptionQuote:
    day: date
    contract: str                  # 契約: TXO, TEO …
    month: str                     # 到期月份(週別): "202501", "202501W2", "202610F4"
    strike: Optional[Decimal]      # 履約價 as published ("20500.0000")
    call_put: str                  # 買賣權: 買權 / 賣權
    open: Optional[Decimal]
    high: Optional[Decimal]
    low: Optional[Decimal]
    close: Optional[Decimal]
    volume: Optional[int]
    settlement: Optional[Decimal]
    open_interest: Optional[int]
    best_bid: Optional[Decimal]
    best_ask: Optional[Decimal]
    session: str


def futures_quotes(client: TWSEAPIClient, contract: str, start: date, end: date) -> Optional[List[FuturesQuote]]:
    """Every futures quote of ``contract`` (or ALL_CONTRACTS) from ``start`` to ``end``, or None when TAIFEX has
    none. Raises ``UpstreamFormatError`` if the columns changed."""
    table = download_table(client, FUT_DATA_DOWN_URL, "futDataDown", FUTURES_FIELDS, start, end,
                           down_type="1", commodity_id=contract, commodity_id2="")
    if table is None:
        return None
    col, rows = table
    return [FuturesQuote(
        day=trade_date(r[col["交易日期"]], "futDataDown"),
        contract=r[col["契約"]].strip(),
        month=r[col["到期月份(週別)"]].strip(),
        open=number(r[col["開盤價"]]),
        high=number(r[col["最高價"]]),
        low=number(r[col["最低價"]]),
        close=number(r[col["收盤價"]]),
        change=number(r[col["漲跌價"]]),
        change_pct=r[col["漲跌%"]].strip(),
        volume=count(r[col["成交量"]]),
        settlement=number(r[col["結算價"]]),
        open_interest=count(r[col["未沖銷契約數"]]),
        best_bid=number(r[col["最後最佳買價"]]),
        best_ask=number(r[col["最後最佳賣價"]]),
        session=r[col["交易時段"]].strip(),
    ) for r in rows]


def option_quotes(client: TWSEAPIClient, contract: str, start: date, end: date) -> Optional[List[OptionQuote]]:
    """Every option quote of ``contract`` (or ALL_CONTRACTS) from ``start`` to ``end``, or None when TAIFEX has
    none. Raises ``UpstreamFormatError`` if the columns changed."""
    table = download_table(client, OPT_DATA_DOWN_URL, "optDataDown", OPTIONS_FIELDS, start, end,
                           down_type="1", commodity_id=contract, commodity_id2="")
    if table is None:
        return None
    col, rows = table
    return [OptionQuote(
        day=trade_date(r[col["交易日期"]], "optDataDown"),
        contract=r[col["契約"]].strip(),
        month=r[col["到期月份(週別)"]].strip(),
        strike=number(r[col["履約價"]]),
        call_put=r[col["買賣權"]].strip(),
        open=number(r[col["開盤價"]]),
        high=number(r[col["最高價"]]),
        low=number(r[col["最低價"]]),
        close=number(r[col["收盤價"]]),
        volume=count(r[col["成交量"]]),
        settlement=number(r[col["結算價"]]),
        open_interest=count(r[col["未沖銷契約數"]]),
        best_bid=number(r[col["最後最佳買價"]]),
        best_ask=number(r[col["最後最佳賣價"]]),
        session=r[col["交易時段"]].strip(),
    ) for r in rows]


def has_regular_session(quotes: Sequence[Union[FuturesQuote, OptionQuote]]) -> bool:
    """A day counts as the latest trading day only once its 一般 (regular) session is in.

    During the regular session the download pages already list today's date with just the overnight
    盤後 rows, which would pass for a whole day.
    """
    return any(q.session == REGULAR_SESSION for q in quotes)
