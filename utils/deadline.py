"""A time budget shared by every upstream request a piece of work makes.

FastMCP 4's ``@mcp.tool(timeout=)`` cannot stop a sync tool: the worker thread shields the
cancellation, so the client still waits for the tool to finish and then gets an error instead of
its result (measured 2026-10-21 on FastMCP 4.1.3: ``timeout=1`` on a 3 s sync tool answered after
3.2 s with the result thrown away). Our tools are sync, so the limit is enforced where their time
goes — in the upstream requests. Inside ``time_budget(seconds)``, ``TWSEAPIClient`` cuts each
request's timeout to what is left of the budget and, once nothing is left, raises
``DeadlineExceeded`` instead of sending the next request. Nothing is left running in the
background, and the site's lock is released as usual.

requests' timeout bounds connecting and each wait for data, not a whole transfer, so a large
download that keeps receiving data can run past the budget; the budget is checked again before the
next request. Cached responses cost no time and do not count.
"""

import time
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Iterator, Optional, Tuple

from .errors import DeadlineExceeded


@dataclass
class _Budget:
    seconds: float
    end: float
    hint: str
    requests: int = 0

    def exceeded(self) -> DeadlineExceeded:
        return DeadlineExceeded(f"超過 {self.seconds:g} 秒仍未完成（已送出 {self.requests} 個請求）；{self.hint}")


# Tools run in worker threads, each in its own copy of the context, so a budget set by one call
# is invisible to every other call.
_current: ContextVar[Optional[_Budget]] = ContextVar("time_budget", default=None)


@contextmanager
def time_budget(seconds: float, hint: str = "請稍後再試") -> Iterator[None]:
    """Give the upstream requests made inside the block ``seconds`` in total.

    ``hint`` ends the error message (what the caller can do instead). Usable as a decorator. A
    nested budget never extends the one around it.
    """
    outer = _current.get()
    end = time.monotonic() + seconds
    if outer is not None:
        end = min(end, outer.end)
    token = _current.set(_Budget(seconds, end, hint))
    try:
        yield
    finally:
        _current.reset(token)


def request_timeout(timeout: float) -> Tuple[float, bool]:
    """(timeout for the next request, whether the budget shortened it).

    Raises ``DeadlineExceeded`` when the current budget is used up. Without a budget the timeout
    is returned unchanged.
    """
    budget = _current.get()
    if budget is None:
        return timeout, False
    left = budget.end - time.monotonic()
    if left <= 0:
        raise budget.exceeded()
    budget.requests += 1
    return (left, True) if left < timeout else (timeout, False)


def budget_exceeded() -> DeadlineExceeded:
    """The error for a request that timed out because the budget shortened its timeout."""
    budget = _current.get()
    return budget.exceeded() if budget is not None else DeadlineExceeded("超過時間上限仍未完成")
