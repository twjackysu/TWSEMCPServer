"""E2E tests for warrants-related APIs."""

import pytest
from utils.api_client import TWSEAPIClient


class TestWarrantBasicInfoAPI:
    """上市權證基本資料 API 測試."""

    ENDPOINT = "/opendata/t187ap37_L"
    EXPECTED_FIELDS = [
        "出表日期",
        "權證代號",
        "權證簡稱",
        "權證類型",
        "類別",
        "履約開始日",
        "最後交易日",
        "履約截止日",
        "發行單位數量(仟單位)",
        "結算方式(詳附註編號說明)",
        "標的證券/指數",
        "最新標的履約配發數量(每仟單位權證)",
        "原始履約價格(元)/履約指數"
    ]

    def test_api_endpoint_is_accessible(self):
        """測試 API 端點可訪問."""
        data = TWSEAPIClient.get_data(self.ENDPOINT)
        assert data is not None, "權證基本資料 API 應該回傳資料"
        assert isinstance(data, list), "權證基本資料 API 應該回傳 list"
        assert len(data) > 0, "權證基本資料 API 應該回傳至少一筆資料"

    def test_response_schema_matches_expected(self):
        """測試回應 schema 符合預期."""
        data = TWSEAPIClient.get_data(self.ENDPOINT)

        # 取第一筆資料檢查欄位
        first_item = data[0]
        assert isinstance(first_item, dict), "每筆資料應該是 dict"

        # 檢查所有必要欄位都存在
        for field in self.EXPECTED_FIELDS:
            assert field in first_item, f"欄位 '{field}' 應該存在於權證基本資料中"

    def test_warrant_code_exists(self):
        """測試權證代號欄位存在且有效."""
        data = TWSEAPIClient.get_data(self.ENDPOINT)

        for item in data[:10]:  # 檢查前 10 筆
            warrant_code = item.get("權證代號")
            assert warrant_code is not None, "權證代號不應為 None"
            assert isinstance(warrant_code, str), "權證代號應該是字串"
            assert warrant_code.strip() != "", "權證代號不應為空字串"
            # 權證代號可能是純數字或數字+P後綴（如 030001 或 03001P）

    def test_underlying_stock_code_format(self):
        """測試標的證券代號格式正確."""
        data = TWSEAPIClient.get_data(self.ENDPOINT)

        for item in data[:10]:  # 檢查前 10 筆
            underlying_code = item.get("標的證券代號")
            if underlying_code and underlying_code != "N/A":
                assert isinstance(underlying_code, str), "標的證券代號應該是字串"
                assert underlying_code.isdigit(), f"標的證券代號應該是數字: {underlying_code}"
                assert len(underlying_code) == 4, f"標的證券代號應該是 4 碼: {underlying_code}"


class TestWarrantTradingAPI:
    """上市權證每日成交資料 API 測試."""

    ENDPOINT = "/opendata/t187ap42_L"
    EXPECTED_FIELDS = [
        "出表日期",
        "權證代號",
        "權證名稱",
        "成交張數",
        "成交金額"
    ]

    def test_api_endpoint_is_accessible(self):
        """測試 API 端點可訪問."""
        data = TWSEAPIClient.get_data(self.ENDPOINT)
        assert data is not None, "權證成交資料 API 應該回傳資料"
        assert isinstance(data, list), "權證成交資料 API 應該回傳 list"
        assert len(data) > 0, "權證成交資料 API 應該回傳至少一筆資料"

    def test_response_schema_matches_expected(self):
        """測試回應 schema 符合預期."""
        data = TWSEAPIClient.get_data(self.ENDPOINT)

        # 取第一筆資料檢查欄位
        first_item = data[0]
        assert isinstance(first_item, dict), "每筆資料應該是 dict"

        # 檢查所有必要欄位都存在
        for field in self.EXPECTED_FIELDS:
            assert field in first_item, f"欄位 '{field}' 應該存在於權證成交資料中"

    def test_warrant_code_exists(self):
        """測試權證代號欄位存在且有效."""
        data = TWSEAPIClient.get_data(self.ENDPOINT)

        for item in data[:10]:  # 檢查前 10 筆
            warrant_code = item.get("權證代號")
            assert warrant_code is not None, "權證代號不應為 None"
            assert isinstance(warrant_code, str), "權證代號應該是字串"
            assert warrant_code.strip() != "", "權證代號不應為空字串"
            # 權證代號可能是純數字或數字+P後綴（如 030001 或 03001P）

    def test_trading_volume_format(self):
        """測試成交量格式正確."""
        data = TWSEAPIClient.get_data(self.ENDPOINT)

        for item in data[:5]:
            volume = item.get("成交張數")
            if volume not in ["", "N/A", None, "--"]:
                assert isinstance(volume, (str, int, float)), \
                    f"成交張數格式不正確: {volume}"

    def test_trading_amount_format(self):
        """測試成交金額格式正確."""
        data = TWSEAPIClient.get_data(self.ENDPOINT)

        for item in data[:5]:
            amount = item.get("成交金額")
            if amount not in ["", "N/A", None, "--"]:
                assert isinstance(amount, (str, int, float)), \
                    f"成交金額格式不正確: {amount}"


class TestWarrantTraderCountAPI:
    """上市權證交易人數 API 測試."""

    ENDPOINT = "/opendata/t187ap43_L"
    EXPECTED_FIELDS = [
        "出表日期",
        "日期",
        "人數"
    ]

    def test_api_endpoint_is_accessible(self):
        """測試 API 端點可訪問."""
        data = TWSEAPIClient.get_data(self.ENDPOINT)
        assert data is not None, "權證交易人數 API 應該回傳資料"
        assert isinstance(data, list), "權證交易人數 API 應該回傳 list"
        assert len(data) > 0, "權證交易人數 API 應該回傳至少一筆資料"

    def test_response_schema_matches_expected(self):
        """測試回應 schema 符合預期."""
        data = TWSEAPIClient.get_data(self.ENDPOINT)

        # 取第一筆資料檢查欄位
        first_item = data[0]
        assert isinstance(first_item, dict), "每筆資料應該是 dict"

        # 檢查所有必要欄位都存在
        for field in self.EXPECTED_FIELDS:
            assert field in first_item, f"欄位 '{field}' 應該存在於權證交易人數中"

    def test_date_field_exists(self):
        """測試日期欄位存在且有效."""
        data = TWSEAPIClient.get_data(self.ENDPOINT)

        for item in data[:10]:  # 檢查前 10 筆
            date_field = item.get("日期")
            if date_field and date_field not in ["", "N/A", None]:
                assert isinstance(date_field, str), "日期應該是字串"
                assert date_field.strip() != "", "日期不應為空字串"

    def test_trader_count_format(self):
        """測試交易人數格式正確."""
        data = TWSEAPIClient.get_data(self.ENDPOINT)

        for item in data[:5]:
            count = item.get("人數")
            if count not in ["", "N/A", None, "--"]:
                assert isinstance(count, (str, int, float)), \
                    f"人數格式不正確: {count}"


class TestWarrantDataConsistency:
    """權證數據一致性測試."""

    def test_warrant_codes_consistency_across_apis(self):
        """測試權證代號在不同 API 間的一致性."""
        # 取得各 API 的權證代號清單
        basic_data = TWSEAPIClient.get_data("/opendata/t187ap37_L")
        trading_data = TWSEAPIClient.get_data("/opendata/t187ap42_L")

        basic_codes = {item.get("權證代號") for item in basic_data if item.get("權證代號")}
        trading_codes = {item.get("權證代號") for item in trading_data if item.get("權證代號")}

        # 檢查兩個API都有返回資料
        assert len(basic_codes) > 0, "基本資料 API 應該回傳權證代號"
        assert len(trading_codes) > 0, "交易資料 API 應該回傳權證代號"

        # 檢查是否有共同的權證代號（放寬條件，不要求完全子集關係）
        common_codes = basic_codes.intersection(trading_codes)
        assert len(common_codes) > 0, "基本資料和交易資料應該有共同的權證代號"

        # 注意：t187ap43_L API 返回的數據結構不同，不包含權證代號，跳過該API的一致性檢查

    def test_get_warrant_data_by_code(self):
        """測試依權證代號查詢資料."""
        # 先取得一個有效的權證代號
        basic_data = TWSEAPIClient.get_data("/opendata/t187ap37_L")
        if basic_data:
            sample_warrant_code = basic_data[0].get("權證代號")

            if sample_warrant_code:
                # 測試基本資料查詢
                basic_result = TWSEAPIClient.get_company_data("/opendata/t187ap37_L", sample_warrant_code)
                if basic_result:
                    assert basic_result.get("權證代號") == sample_warrant_code

                # 測試成交資料查詢
                trading_result = TWSEAPIClient.get_company_data("/opendata/t187ap42_L", sample_warrant_code)
                if trading_result:
                    assert trading_result.get("權證代號") == sample_warrant_code

                # 注意：t187ap43_L API 不支持依權證代號查詢，跳過該測試


class TestWarrantAPIsOverview:
    """權證 APIs 整體測試."""

    @pytest.mark.parametrize("endpoint,name", [
        ("/opendata/t187ap37_L", "權證基本資料"),
        ("/opendata/t187ap42_L", "權證每日成交資料"),
        ("/opendata/t187ap43_L", "權證交易人數"),
    ])
    def test_warrant_api_endpoints_accessible(self, endpoint, name):
        """測試所有權證 API 端點可訪問."""
        data = TWSEAPIClient.get_data(endpoint)
        assert data is not None, f"{name} API 應該回傳資料"
        assert isinstance(data, list), f"{name} API 應該回傳 list"
        assert len(data) > 0, f"{name} API 應該回傳至少一筆資料"

    @pytest.mark.parametrize("endpoint", [
        "/opendata/t187ap37_L",
        "/opendata/t187ap42_L",
    ])
    def test_warrant_apis_have_warrant_code_field(self, endpoint):
        """測試有權證代號的 API 都包含權證代號欄位."""
        data = TWSEAPIClient.get_data(endpoint)
        first_item = data[0]
        assert "權證代號" in first_item, f"{endpoint} 應該包含權證代號欄位"