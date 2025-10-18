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
        "標的證券代號",
        "標的證券簡稱",
        "發行人",
        "履約價格",
        "權證種類",
        "存續期間(月)",
        "發行單位數(仟單位)",
        "履約比例",
        "到期日"
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

    def test_warrant_code_format(self):
        """測試權證代號格式正確."""
        data = TWSEAPIClient.get_data(self.ENDPOINT)

        for item in data[:10]:  # 檢查前 10 筆
            warrant_code = item.get("權證代號")
            assert warrant_code is not None, "權證代號不應為 None"
            assert isinstance(warrant_code, str), "權證代號應該是字串"
            # 權證代號通常是6碼數字
            assert warrant_code.isdigit(), f"權證代號應該是數字: {warrant_code}"
            assert len(warrant_code) == 6, f"權證代號應該是 6 碼: {warrant_code}"

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
        "權證簡稱",
        "成交股數",
        "成交筆數",
        "成交金額",
        "開盤價",
        "最高價",
        "最低價",
        "收盤價",
        "漲跌",
        "漲跌價差",
        "最後揭示買價",
        "最後揭示賣價"
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

    def test_warrant_code_format(self):
        """測試權證代號格式正確."""
        data = TWSEAPIClient.get_data(self.ENDPOINT)

        for item in data[:10]:  # 檢查前 10 筆
            warrant_code = item.get("權證代號")
            assert warrant_code is not None, "權證代號不應為 None"
            assert isinstance(warrant_code, str), "權證代號應該是字串"
            assert warrant_code.isdigit(), f"權證代號應該是數字: {warrant_code}"
            assert len(warrant_code) == 6, f"權證代號應該是 6 碼: {warrant_code}"

    def test_trading_volume_format(self):
        """測試成交量格式正確."""
        data = TWSEAPIClient.get_data(self.ENDPOINT)

        for item in data[:5]:
            volume = item.get("成交股數")
            if volume not in ["", "N/A", None, "--"]:
                assert isinstance(volume, (str, int, float)), \
                    f"成交股數格式不正確: {volume}"

    def test_price_format(self):
        """測試價格格式正確."""
        data = TWSEAPIClient.get_data(self.ENDPOINT)

        price_fields = ["開盤價", "最高價", "最低價", "收盤價"]
        for item in data[:5]:
            for field in price_fields:
                price = item.get(field)
                if price not in ["", "N/A", None, "--"]:
                    assert isinstance(price, (str, int, float)), \
                        f"{field}格式不正確: {price}"


class TestWarrantTraderCountAPI:
    """上市權證交易人數 API 測試."""

    ENDPOINT = "/opendata/t187ap43_L"
    EXPECTED_FIELDS = [
        "出表日期",
        "權證代號",
        "權證簡稱",
        "買進人數",
        "賣出人數",
        "買賣超人數"
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

    def test_warrant_code_format(self):
        """測試權證代號格式正確."""
        data = TWSEAPIClient.get_data(self.ENDPOINT)

        for item in data[:10]:  # 檢查前 10 筆
            warrant_code = item.get("權證代號")
            assert warrant_code is not None, "權證代號不應為 None"
            assert isinstance(warrant_code, str), "權證代號應該是字串"
            assert warrant_code.isdigit(), f"權證代號應該是數字: {warrant_code}"
            assert len(warrant_code) == 6, f"權證代號應該是 6 碼: {warrant_code}"

    def test_trader_count_format(self):
        """測試交易人數格式正確."""
        data = TWSEAPIClient.get_data(self.ENDPOINT)

        count_fields = ["買進人數", "賣出人數", "買賣超人數"]
        for item in data[:5]:
            for field in count_fields:
                count = item.get(field)
                if count not in ["", "N/A", None, "--"]:
                    assert isinstance(count, (str, int, float)), \
                        f"{field}格式不正確: {count}"


class TestWarrantDataConsistency:
    """權證數據一致性測試."""

    def test_warrant_codes_consistency_across_apis(self):
        """測試權證代號在不同 API 間的一致性."""
        # 取得各 API 的權證代號清單
        basic_data = TWSEAPIClient.get_data("/opendata/t187ap37_L")
        trading_data = TWSEAPIClient.get_data("/opendata/t187ap42_L")
        trader_data = TWSEAPIClient.get_data("/opendata/t187ap43_L")

        basic_codes = {item.get("權證代號") for item in basic_data if item.get("權證代號")}
        trading_codes = {item.get("權證代號") for item in trading_data if item.get("權證代號")}
        trader_codes = {item.get("權證代號") for item in trader_data if item.get("權證代號")}

        # 交易資料和交易人數的權證代號應該是基本資料的子集
        assert trading_codes.issubset(basic_codes), \
            "權證成交資料的權證代號應該存在於基本資料中"

        assert trader_codes.issubset(basic_codes), \
            "權證交易人數的權證代號應該存在於基本資料中"

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

                # 測試交易人數查詢
                trader_result = TWSEAPIClient.get_company_data("/opendata/t187ap43_L", sample_warrant_code)
                if trader_result:
                    assert trader_result.get("權證代號") == sample_warrant_code


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
        "/opendata/t187ap43_L",
    ])
    def test_warrant_apis_have_warrant_code_field(self, endpoint):
        """測試所有權證 API 都有權證代號欄位."""
        data = TWSEAPIClient.get_data(endpoint)
        first_item = data[0]
        assert "權證代號" in first_item, f"{endpoint} 應該包含權證代號欄位"