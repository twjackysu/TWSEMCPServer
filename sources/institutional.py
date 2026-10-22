"""三大法人 records both markets' gateways return: per-stock flows, and market-level amounts.

TWSE T86 (``sources/twse/t86.py``) and TPEx insti/dailyTrade (``sources/tpex/insti_daily.py``) publish
the same investor groups in different layouts — T86 under named columns that changed twice since
2012, TPEx under seven identical 買進/賣出/買賣超 headings that only their order tells apart. Each
gateway adapts its layout to ``InstitutionalFlow``, so ranking and display code sees neither.
"""

from dataclasses import dataclass
from typing import List, Optional

from utils.errors import UpstreamFormatError
from utils.parse import int_or_none


@dataclass(frozen=True)
class Trades:
    """Shares one investor group bought, sold and net bought. ``buy`` / ``sell`` are None where the
    source publishes only the net (T86's 自營商 total once it was split into 自行買賣 and 避險)."""
    buy: Optional[int]
    sell: Optional[int]
    net: int


@dataclass(frozen=True)
class InstitutionalFlow:
    code: str
    name: str
    foreign: Trades                      # 外資（及陸資）, 外資自營商 included
    foreign_ex_dealer: Optional[Trades]  # 外資及陸資（不含外資自營商）; None before T86 split it out
    foreign_dealer: Optional[Trades]     # 外資自營商; None likewise
    trust: Trades                        # 投信
    dealer: Trades                       # 自營商 total
    dealer_self: Optional[Trades]        # 自營商（自行買賣）; None in T86's oldest layout
    dealer_hedge: Optional[Trades]       # 自營商（避險）; None likewise
    total_net: int                       # 三大法人買賣超

    def net(self, investor: str) -> int:
        """Net shares bought by "total", "foreign", "trust" or "dealer"."""
        if investor == "foreign":
            return self.foreign.net
        if investor == "trust":
            return self.trust.net
        if investor == "dealer":
            return self.dealer.net
        return self.total_net


@dataclass(frozen=True)
class FlowDay:
    date: str    # YYYYMMDD the report is for
    title: str
    flows: List[InstitutionalFlow]


@dataclass(frozen=True)
class InstitutionalAmount:
    """One row of a market-level 三大法人 amounts table (TWSE BFI82U, TPEx insti/summary)."""
    name: str             # 單位名稱 as published, stripped: "外資及陸資(不含外資自營商)", "外資自營商", "合計"
    buy: Optional[int]    # 買進金額 (NT$)
    sell: Optional[int]   # 賣出金額 (NT$)
    net: Optional[int]    # 買賣差額 / 買賣超 (NT$) = buy - sell


def shares(text, source: str, column: str) -> int:
    """A share count as published ("-1,234,000"); anything else means the layout changed."""
    value = int_or_none(text)
    if value is None:
        raise UpstreamFormatError(f"{source} 的「{column}」不是股數：{text!r}")
    return value
