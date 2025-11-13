"""TWSE API client utilities."""

import requests
import logging
import time
import os
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class TWSEAPIClient:
    """Client for Taiwan Stock Exchange API."""
    
    BASE_URL = "https://openapi.twse.com.tw/v1"
    USER_AGENT = "stock-mcp/1.0"
    _last_request_time = 0
    # 從環境變數讀取 API 請求間隔，預設為 0.5 秒
    _min_request_interval = float(os.getenv('API_REQUEST_DELAY', '0.5'))
    
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
        # 實施速率限制，避免被視為 DDOS 攻擊
        current_time = time.time()
        time_since_last_request = current_time - cls._last_request_time
        if time_since_last_request < cls._min_request_interval:
            sleep_time = cls._min_request_interval - time_since_last_request
            logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f} seconds")
            time.sleep(sleep_time)
        
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
            
            # 更新最後請求時間
            cls._last_request_time = time.time()
            
            # 設定正確的編碼 (UTF-8)
            resp.encoding = 'utf-8'
            # 嘗試解析 JSON；若格式異常（例如少數舊靜態 API 回傳非 JSON），則回傳空陣列避免拋錯
            try:
                data = resp.json()
            except Exception as parse_err:
                logger.warning(f"Response is not valid JSON for {url}: {parse_err}; returning empty list for robustness")
                return []

            return data if isinstance(data, list) else ([data] if data else [])
            
        except Exception as e:
            logger.error(f"Failed to fetch data from {url}: {e}")
            raise
    
    @classmethod
    def get_company_data(cls, endpoint: str, code: str, timeout: float = 30.0) -> Optional[Dict[str, Any]]:
        """
        Fetch company or warrant specific data from TWSE API.

        Args:
            endpoint: API endpoint path
            code: Company stock code or warrant code
            timeout: Request timeout in seconds

        Returns:
            Dictionary containing company/warrant data or None if not found
        """
        try:
            data = cls.get_data(endpoint, timeout)
            # Filter data by company/warrant code
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
    
    @classmethod
    def get_latest_market_data(cls, endpoint: str, count: Optional[int] = None, timeout: float = 30.0) -> List[Dict[str, Any]]:
        """
        Fetch latest market data from TWSE API.
        
        Args:
            endpoint: API endpoint path
            count: Number of latest records to return. If None, returns all records.
            timeout: Request timeout in seconds
            
        Returns:
            List of latest market data records
        """
        try:
            data = cls.get_data(endpoint, timeout)
            # Return latest records or all data if count is None
            return data[-count:] if data and count is not None else data
            
        except Exception as e:
            logger.error(f"Failed to fetch latest market data: {e}")
            return []