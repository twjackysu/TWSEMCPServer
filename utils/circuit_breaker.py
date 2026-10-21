"""Per-site circuit breaker: stop calling a site that keeps failing or has started refusing us.

Retrying a site that is down, or that has blocked our IP, only adds requests at the moment they
do the most harm: an exchange's firewall extends a block while the requests keep coming (on
2026-10-21 www.twse.com.tw answered a script that re-requested one page every 0.5 s for minutes
with non-JSON bodies, and recovered a few minutes after it stopped). So per site (``throttle_key``,
the same unit the throttle uses, since one exchange's subdomains share a firewall):

- ``threshold`` failures in a row open the circuit; a refusal (``Failure.blocked``: HTTP 403 /
  429, MOPS' ``FOR SECURITY REASONS`` page) opens it at once.
- While open, requests to the site fail fast with ``UpstreamUnavailable`` instead of being sent;
  cached responses are still served (the cache sits in front of the request).
- After the cooldown the next request goes through as a probe. Success closes the circuit; a
  failure reopens it with the cooldown doubled, up to ``max_cooldown``. A ``Retry-After`` the
  site sends is honoured when it asks for longer.

What counts as a failure is decided by ``failure_of_exception`` / ``failure_of_response``:
connection errors, timeouts, truncated bodies, HTTP 5xx after the transport's own retries,
refusals, and — for requests that expect JSON — an empty body or an HTML page (TWSE's
maintenance page, block pages). Other non-JSON bodies are not counted: openapi.taifex.com.tw
sometimes serves one endpoint's CSV form for minutes while the rest of the site works, and that
must not cool down taifex.com.tw as a whole. Other 4xx mean the request was wrong, not the site.
"""

import logging
import math
import threading
import time
from dataclasses import dataclass
from typing import Callable, Dict, Optional

import requests

from .errors import UpstreamUnavailable

logger = logging.getLogger(__name__)

BLOCK_PAGE_MARKERS = (b"FOR SECURITY REASONS",)  # MOPS' anti-scraping page
BLOCKED_STATUSES = frozenset({403, 429})


@dataclass(frozen=True)
class Failure:
    reason: str
    blocked: bool = False      # the site refused us: open now instead of after `threshold` failures
    retry_after: float = 0.0   # seconds the site asked us to wait (Retry-After), if any


def failure_of_exception(exc: BaseException) -> Optional[Failure]:
    """The failure an exception from sending a request stands for; None if it says nothing about the site."""
    if isinstance(exc, requests.exceptions.Timeout):
        return Failure("逾時")
    if isinstance(exc, (requests.exceptions.ConnectionError, requests.exceptions.ChunkedEncodingError)):
        return Failure(f"連線失敗（{type(exc).__name__}）")
    if isinstance(exc, requests.exceptions.HTTPError) and exc.response is not None:
        return failure_of_response(exc.response.status_code, b"", expect_json=False, headers=exc.response.headers)
    return None


def failure_of_response(status: int, content: bytes, expect_json: bool, headers=None) -> Optional[Failure]:
    """The failure a received response stands for; None when the site answered normally."""
    if status in BLOCKED_STATUSES:
        return Failure(f"HTTP {status}", blocked=True, retry_after=_retry_after(headers))
    if status >= 500:
        return Failure(f"HTTP {status}", retry_after=_retry_after(headers))
    if status >= 400:
        return None  # our request was wrong; the site is up
    head = content[:4096].upper()
    if any(marker in head for marker in BLOCK_PAGE_MARKERS):
        return Failure("被來源的防爬機制擋下", blocked=True)
    if expect_json:
        body = content.lstrip(b"\xef\xbb\xbf \t\r\n")
        if not body:
            return Failure("空白回應")
        if body[:1] == b"<":
            return Failure("回應是 HTML 頁面而非 JSON（可能被擋或維護中）")
    return None


def _retry_after(headers) -> float:
    value = (headers or {}).get("Retry-After")
    try:
        return max(0.0, float(value)) if value is not None else 0.0
    except ValueError:
        return 0.0  # an HTTP date; not worth parsing for a cooldown hint


@dataclass
class _SiteState:
    failures: int = 0          # in a row
    trips: int = 0             # times opened in a row (doubles the cooldown)
    open_until: float = 0.0
    reason: str = ""


class CircuitBreaker:
    """Thread-safe breaker state for every site. ``threshold`` 0 disables it."""

    def __init__(self, threshold: int = 3, cooldown: float = 30.0, max_cooldown: float = 600.0,
                 clock: Callable[[], float] = time.monotonic):
        self.threshold = threshold
        self.cooldown = cooldown
        self.max_cooldown = max_cooldown
        self._clock = clock
        self._lock = threading.Lock()
        self._sites: Dict[str, _SiteState] = {}

    def check(self, site: str) -> None:
        """Raise ``UpstreamUnavailable`` while ``site`` is cooling down."""
        if self.threshold <= 0:
            return
        with self._lock:
            state = self._sites.get(site)
            remaining = state.open_until - self._clock() if state else 0.0
            reason = state.reason if state else ""
        if remaining > 0:
            raise UpstreamUnavailable(
                f"{site} 暫停查詢中，約 {math.ceil(remaining)} 秒後恢復（{reason}）；"
                f"冷卻期間不送出請求，以免延長來源的封鎖"
            )

    def success(self, site: str) -> None:
        with self._lock:
            state = self._sites.pop(site, None)
        if state is not None and state.trips:
            logger.info(f"Circuit for {site} closed: the probe request succeeded")

    def failure(self, site: str, failure: Failure) -> None:
        if self.threshold <= 0:
            return
        with self._lock:
            state = self._sites.setdefault(site, _SiteState())
            state.failures += 1
            state.reason = (f"連續 {state.failures} 次失敗，最後一次：{failure.reason}"
                            if state.failures > 1 else failure.reason)
            # state.trips: opened before and not closed by a success since, so this was the probe
            if not (failure.blocked or state.trips or state.failures >= self.threshold):
                return
            cooldown = min(self.max_cooldown, max(self.cooldown * 2 ** state.trips, failure.retry_after))
            state.trips += 1
            state.open_until = self._clock() + cooldown
        logger.warning(f"Circuit for {site} open for {cooldown:.0f}s: {state.reason}")
