"""TWSE API client utilities."""

import json
import requests
import logging
import threading
import time
from typing import List, Optional, Any, Dict
from urllib.parse import urlsplit

from .types import TWSEDataItem
from .config import APIConfig
from .circuit_breaker import CircuitBreaker, failure_of_exception, failure_of_response, is_timeout
from .deadline import budget_exceeded, request_timeout
from .http_transport import new_site_session

logger = logging.getLogger(__name__)

# Lock stripes for single-flight: concurrent identical requests wait for the first one
# and read its cached result instead of each hitting upstream.
_FLIGHT_STRIPES = 64


def throttle_key(url: str) -> str:
    """The site a request counts against for rate limiting: the last three host labels.

    openapi./www./mis./mops./mopsov.twse.com.tw all map to ``twse.com.tw``, as do
    www.taifex.com.tw and openapi.taifex.com.tw to ``taifex.com.tw``. Subdomains of one
    exchange may sit behind the same IP-blocking firewall, so they share one interval
    rather than each getting its own and multiplying the rate seen from our IP.
    """
    host = (urlsplit(url).hostname or "").lower()
    return ".".join(host.split(".")[-3:])


class TWSEAPIClient:
    """Client for Taiwan Stock Exchange API."""
    
    # Global instance for backward compatibility
    _instance: Optional['TWSEAPIClient'] = None
    
    def __init__(self,
                 base_url: str = APIConfig.BASE_URL,
                 user_agent: str = APIConfig.USER_AGENT,
                 request_interval: float = APIConfig.REQUEST_INTERVAL,
                 verify_ssl: bool = APIConfig.VERIFY_SSL,
                 cache_ttl: float = APIConfig.CACHE_TTL,
                 breaker: Optional[CircuitBreaker] = None):
        """Initialize the API client."""
        self.base_url = base_url
        self.user_agent = user_agent
        self.request_interval = request_interval
        self.verify_ssl = verify_ssl
        self.cache_ttl = cache_ttl
        # Stops requests to a site that keeps failing or refuses us (utils/circuit_breaker.py).
        self.breaker = breaker if breaker is not None else CircuitBreaker(
            APIConfig.BREAKER_FAILURES, APIConfig.BREAKER_COOLDOWN, APIConfig.BREAKER_MAX_COOLDOWN)
        # Tools run in worker threads (see handle_api_errors), so every piece of shared
        # state below is guarded. One throttle clock and lock per site (throttle_key):
        # requests to one site stay one at a time and spaced, other sites proceed meanwhile.
        self._site_locks: Dict[str, threading.Lock] = {}
        self._site_locks_guard = threading.Lock()
        self._last_request_at: Dict[str, float] = {}
        # One pooled session per site (utils/http_transport.py), used only under that site's lock.
        self._sessions: Dict[str, requests.Session] = {}
        self._flight_locks = [threading.Lock() for _ in range(_FLIGHT_STRIPES)]
        self._cache_guard = threading.Lock()
        self._cache: Dict[str, tuple[float, List[TWSEDataItem]]] = {}
        # Raw response bodies for fetch_json / fetch_bytes calls that opt in with cache_ttl.
        # Bytes, not parsed objects, so no caller can mutate what another caller receives.
        self._response_cache: Dict[str, tuple[float, bytes]] = {}
        self.response_cache_max_entries = APIConfig.RESPONSE_CACHE_MAX_ENTRIES

    @classmethod
    def get_instance(cls) -> 'TWSEAPIClient':
        """Get or create the global singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _site_lock(self, site: str) -> threading.Lock:
        with self._site_locks_guard:
            return self._site_locks.setdefault(site, threading.Lock())

    def _flight_lock(self, key: str) -> threading.Lock:
        return self._flight_locks[hash(key) % _FLIGHT_STRIPES]

    def _throttle(self, site: str) -> None:
        """Wait until ``request_interval`` has passed since the last request to ``site``.

        Called with the site's lock held. Sleeping here blocks only this worker thread.
        Monotonic clock: a wall-clock adjustment must not stretch or skip the wait.
        """
        last = self._last_request_at.get(site)
        if last is None:
            return
        wait = self.request_interval - (time.monotonic() - last)
        if wait > 0:
            logger.debug(f"Rate limiting {site}: sleeping for {wait:.2f} seconds")
            time.sleep(wait)

    def _request(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: float = APIConfig.DEFAULT_TIMEOUT,
        method: str = "GET",
        data: Optional[Dict[str, Any]] = None,
        json_body: Optional[Dict[str, Any]] = None,
        session: Optional[requests.Session] = None,
        expect_json: bool = False,
    ) -> requests.Response:
        """Throttle, send GET/POST, stamp last-request time, and return the response.

        Sent through the site's pooled session (TLS policy and retries: utils/http_transport.py).
        Pass ``session`` for flows that need cookies carried between requests (the TDCC
        query page ties a one-time form token to a JSESSIONID cookie); that session is used as is.
        The outcome goes to the site's circuit breaker; while it is open this raises
        ``UpstreamUnavailable`` without sending. ``expect_json`` lets an empty body or an HTML page
        count as a failure (see utils/circuit_breaker.py). Inside a ``utils.deadline.time_budget``
        the timeout is cut to what is left, and a spent budget raises ``DeadlineExceeded``.
        """
        site = throttle_key(url)
        self.breaker.check(site)  # fail fast rather than queue behind the site lock
        # Held through the request, not just the wait: two threads that both waited out
        # the interval would otherwise send back-to-back. Retries happen inside it too.
        with self._site_lock(site):
            self.breaker.check(site)  # the circuit may have opened while this thread waited
            self._throttle(site)
            # Inside a time_budget: no request once it is spent, and none waits past it.
            timeout, cut_by_budget = request_timeout(timeout)
            logger.info(f"Fetching {method} {url} params={params}")
            own = session is None
            if own:
                session = self._sessions.get(site) or self._sessions.setdefault(
                    site, new_site_session(site, verify=self.verify_ssl))
            try:
                resp = session.request(
                    method,
                    url,
                    params=params,
                    data=data,
                    json=json_body,
                    headers=headers or {"User-Agent": self.user_agent, "Accept": "application/json"},
                    verify=self.verify_ssl,
                    timeout=timeout,
                )
            except requests.RequestException as e:
                if cut_by_budget and is_timeout(e):
                    # Our budget ran out, not the site's patience: not a failure of the site.
                    raise budget_exceeded() from e
                failure = failure_of_exception(e)
                if failure is not None:
                    self.breaker.failure(site, failure)
                raise
            finally:
                # Stamp even when the call raises (timeout, connection error) or the
                # response turns out to be an error status. A failed request still cost the
                # upstream a hit, so leaving the stamp stale would make _throttle() see a
                # huge elapsed time and skip the interval entirely — the retry loops that sit
                # on top of this (MI_MARGN's 7-day walk-back, the industry-report probing in
                # tools/company/financials.py) would then fire back-to-back with no spacing,
                # exactly when TWSE is rate-limiting or down.
                self._last_request_at[site] = time.monotonic()
                if own:
                    session.cookies.clear()  # keep calls stateless; only the pooled connections persist
            # Recorded before the lock is released, so a request queued behind this one sees it.
            failure = failure_of_response(resp.status_code, resp.content, expect_json, getattr(resp, "headers", None))
            if failure is None:
                self.breaker.success(site)
            else:
                self.breaker.failure(site, failure)
        resp.raise_for_status()
        resp.encoding = "utf-8"
        return resp

    def _cached_content(
        self,
        cache_ttl: float,
        url: str,
        params: Optional[Dict[str, Any]],
        headers: Optional[Dict[str, str]],
        timeout: float,
        method: str,
        data: Optional[Dict[str, Any]] = None,
        json_body: Optional[Dict[str, Any]] = None,
        expect_json: bool = False,
    ) -> bytes:
        """Response body for this exact request, served from cache for ``cache_ttl`` seconds.

        Only successful responses are stored (``_request`` raises on HTTP errors). Caching
        is off when the client's global ``cache_ttl`` is 0 (``TWSE_CACHE_TTL=0``).
        """
        if cache_ttl <= 0 or self.cache_ttl <= 0:
            return self._request(url, params=params, headers=headers, timeout=timeout,
                                 method=method, data=data, json_body=json_body, expect_json=expect_json).content
        key = json.dumps([method, url, params, data, json_body], sort_keys=True, ensure_ascii=False, default=str)
        with self._flight_lock(key):
            with self._cache_guard:
                hit = self._response_cache.get(key)
            if hit is not None and time.time() - hit[0] < cache_ttl:
                return hit[1]
            content = self._request(url, params=params, headers=headers, timeout=timeout,
                                    method=method, data=data, json_body=json_body, expect_json=expect_json).content
            with self._cache_guard:
                self._response_cache.pop(key, None)
                while len(self._response_cache) >= self.response_cache_max_entries:
                    # dicts keep insertion order: the first key is the oldest entry
                    self._response_cache.pop(next(iter(self._response_cache)))
                self._response_cache[key] = (time.time(), content)
            return content

    def fetch_data(self, endpoint: str, timeout: float = APIConfig.DEFAULT_TIMEOUT) -> List[TWSEDataItem]:
        """Fetch from a TWSE OpenAPI endpoint (base_url-relative) and normalise to a list.

        Results are cached in-memory per endpoint for ``self.cache_ttl`` seconds. OpenAPI
        list endpoints (company profiles, financials, governance, etc.) change at most daily,
        but a single prompt often triggers several tools that read the same full list within
        seconds of each other — the cache turns those into one HTTP round-trip.
        """
        url = f"{self.base_url}{endpoint}"
        # Tools of one prompt run concurrently and often read the same list: the first
        # fetches it, the rest wait here and read it from the cache.
        with self._flight_lock(url):
            return self._fetch_data_once(url, timeout)

    def _fetch_data_once(self, url: str, timeout: float) -> List[TWSEDataItem]:
        if self.cache_ttl > 0:
            with self._cache_guard:
                cached = self._cache.get(url)
            if cached is not None and time.time() - cached[0] < self.cache_ttl:
                return cached[1]

        try:
            resp = self._request(url, timeout=timeout, expect_json=True)
            try:
                data = resp.json()
            except Exception as parse_err:
                # TWSE serves an HTML maintenance page on some outages. Returning []
                # here would render that as "this endpoint has no data" — a false
                # negative indistinguishable from a genuinely empty result.
                raise ValueError(
                    f"回應不是合法 JSON（來源可能正在維護）: {url}"
                ) from parse_err
            result = data if isinstance(data, list) else ([data] if data else [])
            if self.cache_ttl > 0:
                with self._cache_guard:
                    self._cache[url] = (time.time(), result)
            return result
        except Exception as e:
            logger.error(f"Failed to fetch data from {url}: {e}")
            raise

    def fetch_company_data(self, endpoint: str, code: str, timeout: float = APIConfig.DEFAULT_TIMEOUT) -> Optional[TWSEDataItem]:
        """Fetch one company's record from a list endpoint, or None if absent.

        Failures propagate deliberately. ``None`` means "this endpoint has no row
        for ``code``" and nothing else; swallowing timeouts, 5xx or maintenance
        pages here would collapse "the API is down" into that same ``None`` and
        make every caller report a confident false negative. Callers are tools
        wrapped in ``@handle_api_errors``, which turns the exception into
        ``MSG_QUERY_FAILED``.
        """
        data = self.fetch_data(endpoint, timeout)
        filtered_data = [
            item for item in data
            if isinstance(item, dict) and (
                item.get("公司代號") == code or
                item.get("Code") == code or
                item.get("權證代號") == code
            )
        ]
        return filtered_data[0] if filtered_data else None

    def fetch_latest_market_data(self, endpoint: str, count: Optional[int] = None, timeout: float = APIConfig.DEFAULT_TIMEOUT) -> List[TWSEDataItem]:
        """Fetch the trailing ``count`` records of a list endpoint.

        As with ``fetch_company_data``, failures propagate rather than degrading
        to an empty list — an empty list is a factual claim about the market data.
        """
        data = self.fetch_data(endpoint, timeout)
        return data[-count:] if data and count is not None else data

    def fetch_json(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        timeout: float = APIConfig.DEFAULT_TIMEOUT,
        headers: Optional[Dict[str, str]] = None,
        json_body: Optional[Dict[str, Any]] = None,
        cache_ttl: float = 0,
    ) -> Any:
        """Fetch raw JSON from an arbitrary full URL (not base_url-relative).

        Used for legacy TWSE endpoints and external APIs (mis.twse.com.tw,
        tpex.org.tw, taifex.com.tw) where callers supply the complete URL.
        Passing ``json_body`` sends a POST with that JSON payload instead of a GET
        (mops.twse.com.tw's ``/mops/api/*`` endpoints only accept JSON POSTs).
        ``cache_ttl`` > 0 serves an identical request from memory for that many seconds.
        """
        try:
            method = "POST" if json_body is not None else "GET"
            if cache_ttl > 0:
                content = self._cached_content(cache_ttl, url, params, headers, timeout, method, json_body=json_body,
                                               expect_json=True)
                return json.loads(content.decode("utf-8", errors="replace"))
            return self._request(
                url, params=params, headers=headers, timeout=timeout, method=method, json_body=json_body,
                expect_json=True,
            ).json()
        except Exception as e:
            logger.error(f"Failed to fetch JSON from {url}: {e}")
            raise

    def fetch_bytes(
        self,
        url: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: float = APIConfig.DEFAULT_TIMEOUT,
        method: str = "GET",
        cache_ttl: float = 0,
        session: Optional[requests.Session] = None,
    ) -> bytes:
        """Fetch raw response bytes from an arbitrary full URL, supporting POST form submissions.

        Used for HTML-form download endpoints that return non-JSON bodies (e.g. Big5-encoded
        CSV from www.taifex.com.tw's data-download pages), which callers decode themselves.
        ``cache_ttl`` > 0 serves an identical request from memory for that many seconds.
        A ``session`` makes the call stateful (cookies persist), so it is never cached.
        """
        try:
            if session is not None:
                return self._request(url, params=params, data=data, headers=headers, timeout=timeout,
                                     method=method, session=session).content
            if cache_ttl > 0:
                return self._cached_content(cache_ttl, url, params, headers, timeout, method, data=data)
            return self._request(url, params=params, data=data, headers=headers, timeout=timeout, method=method).content
        except Exception as e:
            logger.error(f"Failed to fetch bytes from {url}: {e}")
            raise

    @classmethod
    def get_json(cls, url: str, params: Optional[Dict[str, Any]] = None, timeout: float = APIConfig.DEFAULT_TIMEOUT) -> Any:
        """Static wrapper for fetch_json."""
        return cls.get_instance().fetch_json(url, params, timeout)

    # --- Static Methods for Backward Compatibility ---

    @classmethod
    def get_data(cls, endpoint: str, timeout: float = APIConfig.DEFAULT_TIMEOUT) -> List[TWSEDataItem]:
        """Static wrapper for backward compatibility."""
        return cls.get_instance().fetch_data(endpoint, timeout)
    
    @classmethod
    def get_company_data(cls, endpoint: str, code: str, timeout: float = APIConfig.DEFAULT_TIMEOUT) -> Optional[TWSEDataItem]:
        """Static wrapper for backward compatibility."""
        return cls.get_instance().fetch_company_data(endpoint, code, timeout)
    
    @classmethod
    def get_latest_market_data(cls, endpoint: str, count: Optional[int] = None, timeout: float = APIConfig.DEFAULT_TIMEOUT) -> List[TWSEDataItem]:
        """Static wrapper for backward compatibility."""
        return cls.get_instance().fetch_latest_market_data(endpoint, count, timeout)
