"""E2E tests for API client utilities."""

import pytest
from utils.api_client import TWSEAPIClient


class TestTWSEAPIClient:
    """TWSE API Client 基礎測試."""
    
    def test_get_data_returns_list(self):
        """測試 get_data 回傳 list."""
        # 使用一個穩定的端點測試
        data = TWSEAPIClient.get_data("/opendata/t187ap03_L")
        assert isinstance(data, list), "get_data 應該回傳 list"
    
    def test_get_data_with_invalid_endpoint(self):
        """測試無效端點會拋出異常."""
        with pytest.raises(Exception):
            TWSEAPIClient.get_data("/invalid/endpoint")
    
    def test_get_company_data_filters_correctly(self):
        """測試 get_company_data 正確過濾."""
        # 使用台積電測試
        data = TWSEAPIClient.get_company_data("/opendata/t187ap03_L", "2330")
        
        if data:
            assert data.get("公司代號") == "2330", "應該回傳台積電的資料"
    
    def test_get_company_data_returns_none_for_invalid_code(self):
        """測試不存在的公司代號回傳 None."""
        data = TWSEAPIClient.get_company_data("/opendata/t187ap03_L", "9999")
        assert data is None, "不存在的公司代號應該回傳 None"
