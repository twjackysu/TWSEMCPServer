"""Find columns by the names an endpoint publishes (its ``fields``), not by position."""

from typing import Any, Dict, List, Optional, Sequence

from utils.errors import UpstreamFormatError


def qualified_fields(fields: Sequence[Any], groups: Sequence[Dict[str, Any]], source: str) -> List[str]:
    """Each column's name prefixed with its group title ("融券/前日餘額"); untitled groups keep the bare name.

    TWSE replies whose groups repeat a field name (TWT93U's 前日餘額, TWTASU's 數量 / 金額) list the groups
    in ``groups`` as ``{"title", "span"}`` covering ``fields`` left to right.
    """
    spans = [int(g.get("span") or 0) for g in groups]
    if sum(spans) != len(fields):
        raise UpstreamFormatError(f"{source} groups 與 fields 對不上：{list(groups)} / {list(fields)}")
    names, i = [], 0
    for g, span in zip(groups, spans, strict=True):
        title = str(g.get("title") or "").strip()
        names += [f"{title}/{str(f).strip()}" if title else str(f).strip() for f in fields[i:i + span]]
        i += span
    return names


def column_index(fields: Optional[Sequence[str]], required: Sequence[str], source: str) -> Dict[str, int]:
    """Position of each ``required`` column in ``fields``; raises if any is missing (or ``fields`` is).

    TWSE's rwd / exchangeReport replies list their column names in ``fields``. Looking columns up
    by name keeps a gateway working when columns are added or reordered, and makes a rename fail
    loudly instead of shifting every value by one.
    """
    names = [str(f).strip() for f in fields or []]
    missing = [name for name in required if name not in names]
    if missing:
        raise UpstreamFormatError(f"{source} 欄位已變更，找不到 {missing}；目前欄位：{names}")
    return {name: names.index(name) for name in required}
