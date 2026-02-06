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

    def fetch_data(self, endpoint: str, timeout: float = APIConfig.DEFAULT_TIMEOUT) -> List[TWSEDataItem]:
        """
        Instance method to fetch data from TWSE API endpoint.
        """
        # Rate limiting logic
        current_time = time.time()
        time_since_last_request = current_time - self._last_request_time
        if time_since_last_request < self.request_interval:
            sleep_time = self.request_interval - time_since_last_request
            logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f} seconds")
            time.sleep(sleep_time)
        
        url = f"{self.base_url}{endpoint}"
        logger.info(f"Fetching TWSE data from {url}")
        
        try:
            resp = requests.get(
                url, 
                headers={"User-Agent": self.user_agent, "Accept": "application/json"}, 
                verify=self.verify_ssl, 
                timeout=timeout
            )
            resp.raise_for_status()
            
            self._last_request_time = time.time()
            resp.encoding = 'utf-8'
            
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
