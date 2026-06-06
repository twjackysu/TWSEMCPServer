"""TWSE API client utilities."""

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
                 verify_ssl: bool = APIConfig.VERIFY_SSL):
        """Initialize the API client."""
        self.base_url = base_url
        self.user_agent = user_agent
        self.request_interval = request_interval
        self.verify_ssl = verify_ssl
        self._last_request_time = 0.0

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
    ) -> requests.Response:
        """Throttle, send GET, stamp last-request time, and return the response."""
        self._throttle()
        logger.info(f"Fetching {url} params={params}")
        resp = requests.get(
            url,
            params=params,
            headers=headers or {"User-Agent": self.user_agent, "Accept": "application/json"},
            verify=self.verify_ssl,
            timeout=timeout,
        )
        resp.raise_for_status()
        self._last_request_time = time.time()
        resp.encoding = "utf-8"
        return resp

    def fetch_data(self, endpoint: str, timeout: float = APIConfig.DEFAULT_TIMEOUT) -> List[TWSEDataItem]:
        """Fetch from a TWSE OpenAPI endpoint (base_url-relative) and normalise to a list."""
        url = f"{self.base_url}{endpoint}"
        try:
            resp = self._request(url, timeout=timeout)
            try:
                data = resp.json()
            except Exception as parse_err:
                logger.warning(f"Response is not valid JSON for {url}: {parse_err}; returning empty list")
                return []
            return data if isinstance(data, list) else ([data] if data else [])
        except Exception as e:
            logger.error(f"Failed to fetch data from {url}: {e}")
            raise

    def fetch_company_data(self, endpoint: str, code: str, timeout: float = APIConfig.DEFAULT_TIMEOUT) -> Optional[TWSEDataItem]:
        """Instance method to fetch company data."""
        try:
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
        except Exception as e:
            logger.error(f"Failed to fetch company data for {code}: {e}")
            return None

    def fetch_latest_market_data(self, endpoint: str, count: Optional[int] = None, timeout: float = APIConfig.DEFAULT_TIMEOUT) -> List[TWSEDataItem]:
        """Instance method to fetch latest market data."""
        try:
            data = self.fetch_data(endpoint, timeout)
            return data[-count:] if data and count is not None else data
        except Exception as e:
            logger.error(f"Failed to fetch latest market data: {e}")
            return []

    def fetch_json(self, url: str, params: Optional[Dict[str, Any]] = None, timeout: float = APIConfig.DEFAULT_TIMEOUT, headers: Optional[Dict[str, str]] = None) -> Any:
        """Fetch raw JSON from an arbitrary full URL (not base_url-relative).

        Used for legacy TWSE endpoints and external APIs (mis.twse.com.tw,
        tpex.org.tw, taifex.com.tw) where callers supply the complete URL.
        """
        try:
            return self._request(url, params=params, headers=headers, timeout=timeout).json()
        except Exception as e:
            logger.error(f"Failed to fetch JSON from {url}: {e}")
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
