"""Numbers as the exchanges print them ("1,234", "2,440.00", "--") into Python values.

One explicit rule per return type, instead of a private _num / to_int in each module whose
behaviour on "--" differs (None in some, 0 in others). Gateways in sources/ use these; the rest
of the repo moves over in Phase 2 (docs/improvement-plan.md).
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
