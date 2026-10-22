"""三大法人 download pages: each identity's trades and open interest, overall, by contract and by call/put.

All five answer a POST of the date range (``commodityId`` = a contract code such as TXF / TXO filters the
by-contract pages on the server; empty = every contract) with a cp950 CSV, one row per day and identity
(自營商 / 投信 / 外資及陸資)::

    totalTableDateDown      日期,身份別, then 12 figures in 百萬元: 多方交易口數,多方交易契約金額(百萬元),空方…,
                            多空交易口數淨額,多空交易契約金額淨額(百萬元),多方未平倉口數,…,多空未平倉契約金額淨額(百萬元)
    futAndOptDateDown       日期,身份別, then the same 12 in 千元, each twice: 期貨多方交易口數,選擇權多方交易口數,…
    futContractsDateDown /  日期,商品名稱,身份別, then the 12 in 千元
    optContractsDateDown
    callsAndPutsDateDown    日期,商品名稱,買賣權別 (CALL / PUT),身份別, then 買方交易口數,買方交易契約金額(千元),賣方…,
                            交易口數買賣淨額,…,未平倉契約金額買賣淨額(千元)

Lots (口數) are whole numbers; amounts are too except the odd "83863.0", so they are kept as published
(Decimal). No thousands separators, no placeholders seen. The pages keep about three years. Columns are found
by name.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Dict, List, Optional, Sequence

from utils.api_client import TWSEAPIClient
from utils.taifex import TAIFEX_DOWNLOAD_BASE

from .download import count, download_table, number, trade_date

TOTAL_TABLE_DATE_DOWN_URL = f"{TAIFEX_DOWNLOAD_BASE}/totalTableDateDown"
FUT_AND_OPT_DATE_DOWN_URL = f"{TAIFEX_DOWNLOAD_BASE}/futAndOptDateDown"
FUT_CONTRACTS_DATE_DOWN_URL = f"{TAIFEX_DOWNLOAD_BASE}/futContractsDateDown"
OPT_CONTRACTS_DATE_DOWN_URL = f"{TAIFEX_DOWNLOAD_BASE}/optContractsDateDown"
CALLS_AND_PUTS_DATE_DOWN_URL = f"{TAIFEX_DOWNLOAD_BASE}/callsAndPutsDateDown"


def long_short_fields(unit: str, prefix: str = "") -> tuple:
    """The 12 long/short column names of a page whose amounts are in ``unit`` (千元 / 百萬元), in Positions order."""
    return tuple(prefix + name for name in (
        "多方交易口數", f"多方交易契約金額({unit})", "空方交易口數", f"空方交易契約金額({unit})",
        "多空交易口數淨額", f"多空交易契約金額淨額({unit})",
        "多方未平倉口數", f"多方未平倉契約金額({unit})", "空方未平倉口數", f"空方未平倉契約金額({unit})",
        "多空未平倉口數淨額", f"多空未平倉契約金額淨額({unit})"))


# callsAndPutsDateDown names the sides 買方 / 賣方 and words the net columns differently.
BUY_SELL_FIELDS = (
    "買方交易口數", "買方交易契約金額(千元)", "賣方交易口數", "賣方交易契約金額(千元)",
    "交易口數買賣淨額", "交易契約金額買賣淨額(千元)",
    "買方未平倉口數", "買方未平倉契約金額(千元)", "賣方未平倉口數", "賣方未平倉契約金額(千元)",
    "未平倉口數買賣淨額", "未平倉契約金額買賣淨額(千元)")


@dataclass(frozen=True)
class Positions:
    """One identity's trades and open interest: lots, and amounts in the page's unit. On the calls/puts page
    long = 買方, short = 賣方."""
    long_volume: Optional[int]
    long_value: Optional[Decimal]
    short_volume: Optional[int]
    short_value: Optional[Decimal]
    net_volume: Optional[int]
    net_value: Optional[Decimal]
    long_oi: Optional[int]
    long_oi_value: Optional[Decimal]
    short_oi: Optional[int]
    short_oi_value: Optional[Decimal]
    net_oi: Optional[int]
    net_oi_value: Optional[Decimal]


@dataclass(frozen=True)
class IdentityPositions:
    """totalTableDateDown: futures and options together, amounts in 百萬元."""
    day: date
    identity: str        # 身份別: 自營商 / 投信 / 外資及陸資
    positions: Positions


@dataclass(frozen=True)
class SplitPositions:
    """futAndOptDateDown: futures and options side by side, amounts in 千元."""
    day: date
    identity: str
    futures: Positions
    options: Positions


@dataclass(frozen=True)
class ContractPositions:
    """fut/optContractsDateDown and callsAndPutsDateDown: one contract, amounts in 千元."""
    day: date
    contract: str        # 商品名稱: 臺股期貨, 臺指選擇權 …
    identity: str
    positions: Positions
    call_put: str = ""   # 買賣權別 CALL / PUT on the calls/puts page


def _positions(r: List[str], col: Dict[str, int], names: Sequence[str]) -> Positions:
    def at(i: int) -> str:
        return r[col[names[i]]]
    return Positions(
        long_volume=count(at(0)), long_value=number(at(1)),
        short_volume=count(at(2)), short_value=number(at(3)),
        net_volume=count(at(4)), net_value=number(at(5)),
        long_oi=count(at(6)), long_oi_value=number(at(7)),
        short_oi=count(at(8)), short_oi_value=number(at(9)),
        net_oi=count(at(10)), net_oi_value=number(at(11)),
    )


def institutional_totals(client: TWSEAPIClient, start: date, end: date) -> Optional[List[IdentityPositions]]:
    """totalTableDateDown from ``start`` to ``end``, or None when TAIFEX has no data for it."""
    fields = long_short_fields("百萬元")
    table = download_table(client, TOTAL_TABLE_DATE_DOWN_URL, "totalTableDateDown", ("日期", "身份別") + fields,
                           start, end)
    if table is None:
        return None
    col, rows = table
    return [IdentityPositions(
        day=trade_date(r[col["日期"]], "totalTableDateDown"),
        identity=r[col["身份別"]].strip(),
        positions=_positions(r, col, fields),
    ) for r in rows]


def institutional_split(client: TWSEAPIClient, start: date, end: date) -> Optional[List[SplitPositions]]:
    """futAndOptDateDown from ``start`` to ``end``, or None when TAIFEX has no data for it."""
    futures, options = long_short_fields("千元", "期貨"), long_short_fields("千元", "選擇權")
    table = download_table(client, FUT_AND_OPT_DATE_DOWN_URL, "futAndOptDateDown",
                           ("日期", "身份別") + futures + options, start, end)
    if table is None:
        return None
    col, rows = table
    return [SplitPositions(
        day=trade_date(r[col["日期"]], "futAndOptDateDown"),
        identity=r[col["身份別"]].strip(),
        futures=_positions(r, col, futures),
        options=_positions(r, col, options),
    ) for r in rows]


def _contract_positions(client: TWSEAPIClient, url: str, source: str, start: date, end: date, code: str,
                        call_put: bool) -> Optional[List[ContractPositions]]:
    fields = BUY_SELL_FIELDS if call_put else long_short_fields("千元")
    keys = ("日期", "商品名稱", "身份別") + (("買賣權別",) if call_put else ())
    table = download_table(client, url, source, keys + fields, start, end, commodityId=code)
    if table is None:
        return None
    col, rows = table
    return [ContractPositions(
        day=trade_date(r[col["日期"]], source),
        contract=r[col["商品名稱"]].strip(),
        identity=r[col["身份別"]].strip(),
        positions=_positions(r, col, fields),
        call_put=r[col["買賣權別"]].strip() if call_put else "",
    ) for r in rows]


def futures_contract_positions(client: TWSEAPIClient, start: date, end: date,
                               code: str = "") -> Optional[List[ContractPositions]]:
    """futContractsDateDown for futures contract ``code`` (TXF, MXF …; "" = every contract), or None."""
    return _contract_positions(client, FUT_CONTRACTS_DATE_DOWN_URL, "futContractsDateDown", start, end, code, False)


def option_contract_positions(client: TWSEAPIClient, start: date, end: date,
                              code: str = "") -> Optional[List[ContractPositions]]:
    """optContractsDateDown for option contract ``code`` (TXO …; "" = every contract), or None."""
    return _contract_positions(client, OPT_CONTRACTS_DATE_DOWN_URL, "optContractsDateDown", start, end, code, False)


def calls_puts_positions(client: TWSEAPIClient, start: date, end: date,
                         code: str = "") -> Optional[List[ContractPositions]]:
    """callsAndPutsDateDown for option contract ``code`` ("" = every contract), CALL and PUT rows apart, or None."""
    return _contract_positions(client, CALLS_AND_PUTS_DATE_DOWN_URL, "callsAndPutsDateDown", start, end, code, True)
