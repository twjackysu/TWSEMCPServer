"""TWSE API client utilities."""

import json
import requests
import logging
import time
from typing import List, Optional, Any, Dict

from .types import TWSEDataItem
from .config import APIConfig

logger = logging.getLogger(__name__)

class TWSEAPIClient:
    """Client for Taiwan Stock Exchange API."""
    
    # Global instance for backward compatibility
    _instance: Optional['TWSEAPIClient'] = None
    
    def __init__(self,
                 base_url: str = APIConfig.BASE_URL,
                 user_agent: str = APIConfig.USER_AGENT,
                 request_interval: float = APIConfig.REQUEST_INTERVAL,
                 verify_ssl: bool = APIConfig.VERIFY_SSL,
                 cache_ttl: float = APIConfig.CACHE_TTL):
        """Initialize the API client."""
        self.base_url = base_url
        self.user_agent = user_agent
        self.request_interval = request_interval
        self.verify_ssl = verify_ssl
        self.cache_ttl = cache_ttl
        self._last_request_time = 0.0
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

    def _throttle(self) -> None:
        """Enforce the per-instance request interval."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self.request_interval:
            wait = self.request_interval - elapsed
            logger.debug(f"Rate limiting: sleeping for {wait:.2f} seconds")
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
    ) -> requests.Response:
        """Throttle, send GET/POST, stamp last-request time, and return the response."""
        self._throttle()
        logger.info(f"Fetching {method} {url} params={params}")
        try:
            resp = requests.request(
                method,
                url,
                params=params,
                data=data,
                json=json_body,
                headers=headers or {"User-Agent": self.user_agent, "Accept": "application/json"},
                verify=self.verify_ssl,
                timeout=timeout,
            )
        finally:
            # Stamp even when the call raises (timeout, connection error) or the
            # response turns out to be an error status. A failed request still cost the
            # upstream a hit, so leaving the stamp stale would make _throttle() see a
            # huge elapsed time and skip the interval entirely — the retry loops that sit
            # on top of this (MI_MARGN's 7-day walk-back, the industry-report probing in
            # tools/company/financials.py) would then fire back-to-back with no spacing,
            # exactly when TWSE is rate-limiting or down.
            self._last_request_time = time.time()
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
    ) -> bytes:
        """Response body for this exact request, served from cache for ``cache_ttl`` seconds.

        Only successful responses are stored (``_request`` raises on HTTP errors). Caching
        is off when the client's global ``cache_ttl`` is 0 (``TWSE_CACHE_TTL=0``).
        """
        if cache_ttl <= 0 or self.cache_ttl <= 0:
            return self._request(url, params=params, headers=headers, timeout=timeout,
                                 method=method, data=data, json_body=json_body).content
        key = json.dumps([method, url, params, data, json_body], sort_keys=True, ensure_ascii=False, default=str)
        now = time.time()
        hit = self._response_cache.get(key)
        if hit is not None and now - hit[0] < cache_ttl:
            return hit[1]
        content = self._request(url, params=params, headers=headers, timeout=timeout,
                                method=method, data=data, json_body=json_body).content
        self._response_cache.pop(key, None)
        while len(self._response_cache) >= self.response_cache_max_entries:
            # dicts keep insertion order: the first key is the oldest entry
            self._response_cache.pop(next(iter(self._response_cache)))
        self._response_cache[key] = (now, content)
        return content

    def fetch_data(self, endpoint: str, timeout: float = APIConfig.DEFAULT_TIMEOUT) -> List[TWSEDataItem]:
        """Fetch from a TWSE OpenAPI endpoint (base_url-relative) and normalise to a list.

        Results are cached in-memory per endpoint for ``self.cache_ttl`` seconds. OpenAPI
        list endpoints (company profiles, financials, governance, etc.) change at most daily,
        but a single prompt often triggers several tools that read the same full list within
        seconds of each other — the cache turns those into one HTTP round-trip.
        """
        url = f"{self.base_url}{endpoint}"

        if self.cache_ttl > 0:
            cached = self._cache.get(url)
            if cached is not None and time.time() - cached[0] < self.cache_ttl:
                return cached[1]

        try:
            resp = self._request(url, timeout=timeout)
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
                content = self._cached_content(cache_ttl, url, params, headers, timeout, method, json_body=json_body)
                return json.loads(content.decode("utf-8", errors="replace"))
            return self._request(
                url, params=params, headers=headers, timeout=timeout, method=method, json_body=json_body
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
    ) -> bytes:
        """Fetch raw response bytes from an arbitrary full URL, supporting POST form submissions.

        Used for HTML-form download endpoints that return non-JSON bodies (e.g. Big5-encoded
        CSV from www.taifex.com.tw's data-download pages), which callers decode themselves.
        ``cache_ttl`` > 0 serves an identical request from memory for that many seconds.
        """
        try:
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
