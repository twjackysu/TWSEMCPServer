"""Shared ranking / display helpers for the 三大法人 (institutional investor) tools.

Used by the listed (TWSE T86 / BFI82U) and OTC (TPEx insti/dailyTrade / insti/summary) tools
so that both markets take the same sort_by / side / category / period values.
"""

from datetime import datetime, timedelta
from typing import Callable, List, Literal, Sequence, TypeVar, Union

from .parse import int_or_none

Row = TypeVar("Row")

SORT_LABELS = {"total": "三大法人合計", "foreign": "外資", "trust": "投信", "dealer": "自營商"}
SIDES = {"abs": "買賣超絕對值", "buy": "買超", "sell": "賣超"}
PERIODS = {"day": "日", "week": "週", "month": "月"}
# The values tools accept (their schema enums); tests/unit/test_literal_params_unit.py keeps each
# equal to the keys of the mapping above it.
Investor = Literal["total", "foreign", "trust", "dealer"]  # SORT_LABELS
Side = Literal["abs", "buy", "sell"]                        # SIDES
Period = Literal["day", "week", "month"]                    # PERIODS


def rank(rows: Sequence[Row], value: Callable[[Row], int], side: str) -> List[Row]:
    """Rows ordered by ``value``: largest net buy first, largest net sell first, or by |value|.

    ``buy`` / ``sell`` keep only rows on that side, so a 買超 ranking never shows sellers.
    """
    if side == "buy":
        return sorted((r for r in rows if value(r) > 0), key=value, reverse=True)
    if side == "sell":
        return sorted((r for r in rows if value(r) < 0), key=value)
    return sorted((r for r in rows if value(r) != 0), key=lambda r: abs(value(r)), reverse=True)


def yi(amount: Union[str, int, None]) -> str:
    """"-68,513,664,272" or -68513664272 (元) → "-685.14 億"."""
    return f"{(int_or_none(amount) or 0) / 1e8:,.2f} 億"


def week_start(day: datetime) -> datetime:
    return day - timedelta(days=day.weekday())
