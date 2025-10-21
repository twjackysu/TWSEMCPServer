"""E2E tests for broker-related APIs."""

import pytest
from utils.api_client import TWSEAPIClient


class TestBrokerServiceAPIs:
    """券商服務相關 APIs 測試."""

    @pytest.mark.parametrize("endpoint,name", [
        ("/brokerService/secRegData", "開辦定期定額業務證券商名單"),
        ("/brokerService/brokerList", "證券商總公司基本資料"),
    ])
    def test_broker_service_api_accessible(self, endpoint, name):
        """測試券商服務相關 API 端點可訪問."""
        data = TWSEAPIClient.get_data(endpoint)
        assert data is not None, f"{name} API 應該回傳資料"
        assert isinstance(data, list), f"{name} API 應該回傳 list"
        assert len(data) > 0, f"{name} API 應該回傳至少一筆資料"

    @pytest.mark.parametrize("endpoint", [
        "/brokerService/secRegData",
        "/brokerService/brokerList",
    ])
    def test_broker_service_apis_have_basic_fields(self, endpoint):
        """測試券商服務相關 APIs 都有基本欄位."""
        data = TWSEAPIClient.get_data(endpoint)
        first_item = data[0]
        # 確保至少有基本欄位存在
        assert len(first_item) > 0, f"{endpoint} 應該至少包含一些欄位"


class TestBrokerDataAPIs:
    """券商資料相關 APIs 測試."""

    @pytest.mark.parametrize("endpoint,name", [
        ("/opendata/t187ap01", "券商業務別人員數"),
        ("/opendata/t187ap20", "各券商每月月計表"),
        ("/opendata/t187ap21", "各券商收支概況表資料"),
        ("/opendata/t187ap18", "證券商基本資料"),
        ("/opendata/OpenData_BRK01", "證券商營業員男女人數統計資料"),
        ("/opendata/OpenData_BRK02", "證券商分公司基本資料"),
    ])
    def test_broker_data_api_accessible(self, endpoint, name):
        """測試券商資料相關 API 端點可訪問."""
        data = TWSEAPIClient.get_data(endpoint)
        assert data is not None, f"{name} API 應該回傳資料"
        assert isinstance(data, list), f"{name} API 應該回傳 list"
        assert len(data) > 0, f"{name} API 應該回傳至少一筆資料"

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
        first_item = data[0]
        # 確保至少有基本欄位存在
        assert len(first_item) > 0, f"{endpoint} 應該至少包含一些欄位"


class TestBrokerAPIsOverview:
    """券商 APIs 整體測試."""

    @pytest.mark.parametrize("endpoint,name", [
        ("/brokerService/secRegData", "開辦定期定額業務證券商名單"),
        ("/brokerService/brokerList", "證券商總公司基本資料"),
        ("/opendata/t187ap01", "券商業務別人員數"),
        ("/opendata/t187ap20", "各券商每月月計表"),
        ("/opendata/t187ap21", "各券商收支概況表資料"),
        ("/opendata/t187ap18", "證券商基本資料"),
        ("/opendata/OpenData_BRK01", "證券商營業員男女人數統計資料"),
        ("/opendata/OpenData_BRK02", "證券商分公司基本資料"),
    ])
    def test_broker_api_endpoints_accessible(self, endpoint, name):
        """測試所有券商 API 端點可訪問."""
        data = TWSEAPIClient.get_data(endpoint)
        assert data is not None, f"{name} API 應該回傳資料"
        assert isinstance(data, list), f"{name} API 應該回傳 list"
        assert len(data) > 0, f"{name} API 應該回傳至少一筆資料"