"""Numbers as the exchanges print them ("1,234", "2,440.00", "14.5%", "--") into Python values.

One explicit rule per return type, shared by the whole repo instead of a private _num / to_int in
each module whose behaviour on "--" differed (None in some, 0 in others). Every function returns
None when there is no number ("--", "-", "", "N/A", None). Where a missing value should count as
zero — sorting by volume, adding amounts up — the caller says so: ``int_or_none(x) or 0``.
"""

from decimal import Decimal, InvalidOperation
from typing import Optional


def _clean(value) -> str:
    return str(value).replace(",", "").strip()


def decimal_or_none(value) -> Optional[Decimal]:
    """'2,440.00' → Decimal('2440.00') keeping the printed digits; None for '--', '', 'N/A'."""
    try:
        return Decimal(_clean(value))
    except InvalidOperation:
        return None


def int_or_none(value) -> Optional[int]:
    """'31,855,287' → 31855287; None for '--', '', 'N/A' or anything that is not a whole number."""
    try:
        return int(_clean(value))
    except ValueError:
        return None


def float_or_none(value) -> Optional[float]:
    """'2,440.00' → 2440.0, '14.5%' → 14.5 (the percentage as printed), 106.64 → 106.64,
    Decimal('2480.00') → 2480.0 (as float(Decimal) gives it); None for '--', '-', '', 'N/A', None."""
    try:
        return float(_clean(value).replace("%", ""))
    except ValueError:
        return None
