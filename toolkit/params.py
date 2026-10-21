"""Parameter types for tool signatures.

FastMCP turns a tool's type hints into its JSON schema and validates every call against it, so an
argument outside the type never reaches the tool: a ``Literal`` becomes an ``enum``, a ``Field``
bound becomes ``minimum`` / ``maximum``, and clients see both before calling. The rejection is
worded in Chinese by ``ArgumentErrorsInChinese`` (toolkit/validation.py). Enumerations live next to
the mapping they index (e.g. ``utils.institutional.Investor`` with ``SORT_LABELS``).
"""

from typing import Annotated

from pydantic import Field

Limit = Annotated[int, Field(ge=1)]   # rows in one reply
Offset = Annotated[int, Field(ge=0)]  # rows skipped before them (paging)


def bounded(low: int, high: int):
    """An int parameter that must lie in ``low``..``high``."""
    return Annotated[int, Field(ge=low, le=high)]
