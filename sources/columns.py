"""Find columns by the names an endpoint publishes (its ``fields``), not by position."""

from typing import Dict, Sequence

from utils.errors import UpstreamFormatError


def column_index(fields: Sequence[str], required: Sequence[str], source: str) -> Dict[str, int]:
    """Position of each ``required`` column in ``fields``; raises if any is missing.

    TWSE's rwd / exchangeReport replies list their column names in ``fields``. Looking columns up
    by name keeps a gateway working when columns are added or reordered, and makes a rename fail
    loudly instead of shifting every value by one.
    """
    names = [str(f).strip() for f in fields or []]
    missing = [name for name in required if name not in names]
    if missing:
        raise UpstreamFormatError(f"{source} 欄位已變更，找不到 {missing}；目前欄位：{names}")
    return {name: names.index(name) for name in required}
