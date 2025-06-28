"""TWSE API client utilities."""

import requests
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class TWSEAPIClient:
    """Client for Taiwan Stock Exchange API."""
    
    BASE_URL = "https://openapi.twse.com.tw/v1"
    USER_AGENT = "stock-mcp/1.0"
    
    @classmethod
    def get_data(cls, endpoint: str, timeout: float = 30.0) -> List[Dict[str, Any]]:
        """
        Fetch data from TWSE API endpoint.
        
        Args:
            endpoint: API endpoint path (e.g., "/opendata/t187ap03_L")
            timeout: Request timeout in seconds
            
        Returns:
            List of dictionaries containing API response data
            
        Raises:
            Exception: If API request fails
        """
        url = f"{cls.BASE_URL}{endpoint}"
        logger.info(f"Fetching TWSE data from {url}")
        
        try:
            # 透過 verify=False 跳過 SSL 憑證驗證
            resp = requests.get(
                url, 
                headers={"User-Agent": cls.USER_AGENT, "Accept": "application/json"}, 
                verify=False, 
                timeout=timeout
            )
            resp.raise_for_status()
            
            # 設定正確的編碼 (UTF-8)
            resp.encoding = 'utf-8'
            data = resp.json()
            
            return data if isinstance(data, list) else [data] if data else []
            
        except Exception as e:
            logger.error(f"Failed to fetch data from {url}: {e}")
            raise
    
    @classmethod
    def get_company_data(cls, endpoint: str, code: str, timeout: float = 30.0) -> Optional[Dict[str, Any]]:
        """
        Fetch company-specific data from TWSE API.
        
        Args:
            endpoint: API endpoint path
            code: Company stock code
            timeout: Request timeout in seconds
            
        Returns:
            Dictionary containing company data or None if not found
        """
        try:
            data = cls.get_data(endpoint, timeout)
            # Filter data by company code
            filtered_data = [
                item for item in data 
                if isinstance(item, dict) and (
                    item.get("公司代號") == code or 
                    item.get("Code") == code
                )
            ]
            return filtered_data[0] if filtered_data else None
            
        except Exception as e:
            logger.error(f"Failed to fetch company data for {code}: {e}")
            return None
    
    @classmethod
    def get_latest_market_data(cls, endpoint: str, count: int = 1, timeout: float = 30.0) -> List[Dict[str, Any]]:
        """
        Fetch latest market data from TWSE API.
        
        Args:
            endpoint: API endpoint path
            count: Number of latest records to return
            timeout: Request timeout in seconds
            
        Returns:
            List of latest market data records
        """
        try:
            data = cls.get_data(endpoint, timeout)
            # Return latest records
            return data[-count:] if data else []
            
        except Exception as e:
            logger.error(f"Failed to fetch latest market data: {e}")
            return []