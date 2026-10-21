"""``limit`` / ``offset`` paging, the same way in every tool.

    paged = Page(limit, offset).take(rows)
    if paged.past_end:
        return paged.out_of_range("…資料")
    header = f"…（共 {paged.total} 筆{'，' + paged.span() if paged.span() else ''}）"
    ...render paged.rows...
    if paged.more():
        lines.append("\\n" + paged.more())

Tools still write their own headers; the slice, the 第 a–b 筆 range, the "… 還有 N 筆" hint and the
past-the-end reply come from here.
"""

from dataclasses import dataclass
from typing import Generic, List, Optional, Sequence, TypeVar

from .constants import MSG_OFFSET_OUT_OF_RANGE
from .errors import InvalidArgument

T = TypeVar("T")


@dataclass(frozen=True)
class Page:
    """A validated ``limit`` / ``offset`` pair. ``max_limit`` caps how many rows one reply may hold."""

    limit: int
    offset: int = 0
    max_limit: Optional[int] = None

    def __post_init__(self):
        if self.limit < 1 or (self.max_limit is not None and self.limit > self.max_limit):
            upper = f"～{self.max_limit}" if self.max_limit is not None else " 以上"
            raise InvalidArgument(f"limit 必須介於 1{upper}（收到 {self.limit}）")
        if self.offset < 0:
            raise InvalidArgument(f"offset 不可為負數（收到 {self.offset}）")

    def take(self, rows: Sequence[T]) -> "Paged[T]":
        return Paged(list(rows[self.offset:self.offset + self.limit]), len(rows), self.offset, self.limit)


@dataclass(frozen=True)
class Paged(Generic[T]):
    """The rows of one page, and how to tell the reader where they sit."""

    rows: List[T]
    total: int
    offset: int
    limit: int

    @property
    def past_end(self) -> bool:
        """There are rows, but ``offset`` skipped all of them."""
        return self.total > 0 and not self.rows

    def out_of_range(self, data_type: str) -> str:
        return MSG_OFFSET_OUT_OF_RANGE.format(offset=self.offset, data_type=data_type, count=self.total)

    def span(self, unit: str = "筆") -> str:
        """"顯示第 51–100 筆" when this page is not everything, else ""."""
        if len(self.rows) >= self.total:
            return ""
        return f"顯示第 {self.offset + 1}–{self.offset + len(self.rows)} {unit}"

    def more(self, unit: str = "筆") -> str:
        """"... 還有 N 筆，使用 offset=X 查看更多" when rows follow this page, else ""."""
        remaining = self.total - self.offset - len(self.rows)
        if remaining <= 0:
            return ""
        return f"... 還有 {remaining} {unit}，使用 offset={self.offset + self.limit} 查看更多"
