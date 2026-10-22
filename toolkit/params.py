"""Parameter types for tool signatures.

FastMCP turns a tool's type hints into its JSON schema and validates every call against it, so an
argument outside the type never reaches the tool: a ``Literal`` becomes an ``enum``, a ``Field``
bound becomes ``minimum`` / ``maximum``, and clients see both before calling. The rejection is
worded in Chinese by ``ArgumentErrorsInChinese`` (toolkit/validation.py). Enumerations live next to
the mapping they index (e.g. ``utils.institutional.Investor`` with ``SORT_LABELS``).
"""

from datetime import datetime
from typing import Annotated

from pydantic import AfterValidator, Field

Limit = Annotated[int, Field(ge=1)]   # rows in one reply
Offset = Annotated[int, Field(ge=0)]  # rows skipped before them (paging)
# An int within a range is written out where it is used, `Annotated[int, Field(ge=1, le=MAX_ROWS)]`: a
# helper returning that type would be a call in an annotation, which type checkers reject.


def _calendar_date(value: str) -> str:
    """The pattern admits 20261301; a date parameter has to name a day that exists."""
    if value:
        try:
            datetime.strptime(value, "%Y%m%d")
        except ValueError:
            raise ValueError("日期不存在") from None
    return value


# Every date a tool takes is a Gregorian (西元) YYYYMMDD string, whatever the upstream wants: the
# tool converts it (ROC 115/09/30 or 1150930 for TWSE / MOPS, 2026/09/30 for TPEx). The value
# reaches the tool unchanged. TradingDate may be "" — the tool's default, usually the latest
# trading day; RequiredTradingDate may not. Neither knows the trading calendar: a holiday passes
# and the upstream answers that it has no data.
DATE_PATTERN = r"^\d{8}$"
TradingDate = Annotated[str, Field(pattern=r"^(\d{8})?$"), AfterValidator(_calendar_date)]
RequiredTradingDate = Annotated[str, Field(pattern=DATE_PATTERN), AfterValidator(_calendar_date)]
