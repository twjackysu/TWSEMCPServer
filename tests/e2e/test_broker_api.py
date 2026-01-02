"""E2E tests for broker-related APIs."""

import pytest
from utils.api_client import TWSEAPIClient


class TestBrokerServiceAPIs:
    """券商服務相關 APIs 測試."""

    @pytest.mark.parametrize("endpoint", [
        "/brokerService/secRegData",
        "/brokerService/brokerList",
    ])
    def test_broker_service_apis_have_basic_fields(self, endpoint):
        """測試券商服務相關 APIs 都有基本欄位."""
        data = TWSEAPIClient.get_data(endpoint)
        # 跳過空資料的測試
        if not data:
            pytest.skip(f"API {self.ENDPOINT} 目前返回空資料")
        
        first_item = data[0]
        # 確保至少有基本欄位存在
        assert len(first_item) > 0, f"{endpoint} 應該至少包含一些欄位"


class TestBrokerDataAPIs:
    """券商資料相關 APIs 測試."""

    @pytest.mark.parametrize("endpoint", [
        "/opendata/t187ap01",
        "/opendata/t187ap20",
        "/opendata/t187ap21",
        "/opendata/t187ap18",
        "/opendata/OpenData_BRK01",
        "/opendata/OpenData_BRK02",
    ])
    def test_broker_data_apis_have_basic_fields(self, endpoint):
        """測試券商資料相關 APIs 都有基本欄位."""
        data = TWSEAPIClient.get_data(endpoint)
        # 跳過空資料的測試
        if not data:
            pytest.skip(f"API {self.ENDPOINT} 目前返回空資料")
        
        first_item = data[0]
        # 確保至少有基本欄位存在
        assert len(first_item) > 0, f"{endpoint} 應該至少包含一些欄位"
