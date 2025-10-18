"""E2E tests for company-related APIs."""

import pytest
from utils.api_client import TWSEAPIClient


class TestCompanyDividendAPI:
    """股利分派情形 API 測試."""

    ENDPOINT = "/opendata/t187ap45_L"
    EXPECTED_FIELDS = [
        "出表日期",
        "股利所屬年度",
        "公司代號",
        "公司名稱",
        "股利政策",
        "董事會決議日",
        "股東會決議日",
        "除息交易日",
        "除息參考價",
        "除權交易日",
        "除權參考價",
        "權息同除交易日",
        "權息同除參考價",
        "股東股利",
        "現金股利",
        "股票股利"
    ]

    def test_api_endpoint_is_accessible(self):
        """測試 API 端點可訪問."""
        data = TWSEAPIClient.get_data(self.ENDPOINT)
        assert data is not None, "API 應該回傳資料"
        assert isinstance(data, list), "API 應該回傳 list"
        assert len(data) > 0, "API 應該回傳至少一筆資料"

    def test_response_schema_matches_expected(self):
        """測試回應 schema 符合預期."""
        data = TWSEAPIClient.get_data(self.ENDPOINT)

        # 取第一筆資料檢查欄位
        first_item = data[0]
        assert isinstance(first_item, dict), "每筆資料應該是 dict"

        # 檢查所有必要欄位都存在
        for field in self.EXPECTED_FIELDS:
            assert field in first_item, f"欄位 '{field}' 應該存在於回應中"

    def test_company_code_format(self):
        """測試公司代號格式正確."""
        data = TWSEAPIClient.get_data(self.ENDPOINT)

        for item in data[:10]:  # 檢查前 10 筆
            code = item.get("公司代號")
            assert code is not None, "公司代號不應為 None"
            assert isinstance(code, str), "公司代號應該是字串"
            assert code.isdigit(), f"公司代號應該是數字: {code}"
            assert len(code) == 4, f"公司代號應該是 4 碼: {code}"

    def test_get_company_data_by_code(self, sample_stock_code):
        """測試依公司代號查詢資料."""
        data = TWSEAPIClient.get_company_data(self.ENDPOINT, sample_stock_code)

        if data:
            assert data.get("公司代號") == sample_stock_code, \
                f"查詢結果應該是指定的公司代號 {sample_stock_code}"


class TestCompanyNewsAPI:
    """上市公司每日重大訊息 API 測試."""

    ENDPOINT = "/opendata/t187ap04_L"
    EXPECTED_FIELDS = [
        "出表日期",
        "公司代號",
        "公司名稱",
        "主旨",
        "符合條款",
        "事實發生日",
        "說明",
        "發言人",
        "發言人職稱",
        "發言人電話",
        "發言人電子郵件",
        "代理發言人",
        "代理發言人職稱",
        "代理發言人電話",
        "代理發言人電子郵件"
    ]

    def test_api_endpoint_is_accessible(self):
        """測試 API 端點可訪問."""
        data = TWSEAPIClient.get_data(self.ENDPOINT)
        assert data is not None, "API 應該回傳資料"
        assert isinstance(data, list), "API 應該回傳 list"
        assert len(data) > 0, "API 應該回傳至少一筆資料"

    def test_response_schema_matches_expected(self):
        """測試回應 schema 符合預期."""
        data = TWSEAPIClient.get_data(self.ENDPOINT)

        # 取第一筆資料檢查欄位
        first_item = data[0]
        assert isinstance(first_item, dict), "每筆資料應該是 dict"

        # 檢查所有必要欄位都存在
        for field in self.EXPECTED_FIELDS:
            assert field in first_item, f"欄位 '{field}' 應該存在於回應中"

    def test_company_code_format(self):
        """測試公司代號格式正確."""
        data = TWSEAPIClient.get_data(self.ENDPOINT)

        for item in data[:10]:  # 檢查前 10 筆
            code = item.get("公司代號")
            assert code is not None, "公司代號不應為 None"
            assert isinstance(code, str), "公司代號應該是字串"
            assert code.isdigit(), f"公司代號應該是數字: {code}"
            assert len(code) == 4, f"公司代號應該是 4 碼: {code}"

    def test_get_company_data_by_code(self, sample_stock_code):
        """測試依公司代號查詢資料."""
        data = TWSEAPIClient.get_company_data(self.ENDPOINT, sample_stock_code)

        if data:
            assert data.get("公司代號") == sample_stock_code, \
                f"查詢結果應該是指定的公司代號 {sample_stock_code}"


class TestCompanyRevenueAPI:
    """上市公司每月營業收入彙總表 API 測試."""

    ENDPOINT = "/opendata/t187ap05_L"
    EXPECTED_FIELDS = [
        "出表日期",
        "資料年月",
        "公司代號",
        "公司名稱",
        "產業別",
        "營業收入-當月營收",
        "營業收入-上月營收",
        "營業收入-去年當月營收",
        "營業收入-上月比較增減(%)",
        "營業收入-去年同月增減(%)",
        "累計營業收入-當月累計營收",
        "累計營業收入-去年累計營收",
        "累計營業收入-前期比較增減(%)",
        "備註"
    ]

    def test_api_endpoint_is_accessible(self):
        """測試 API 端點可訪問."""
        data = TWSEAPIClient.get_data(self.ENDPOINT)
        assert data is not None, "API 應該回傳資料"
        assert isinstance(data, list), "API 應該回傳 list"
        assert len(data) > 0, "API 應該回傳至少一筆資料"

    def test_response_schema_matches_expected(self):
        """測試回應 schema 符合預期."""
        data = TWSEAPIClient.get_data(self.ENDPOINT)

        # 取第一筆資料檢查欄位
        first_item = data[0]
        assert isinstance(first_item, dict), "每筆資料應該是 dict"

        # 檢查所有必要欄位都存在
        for field in self.EXPECTED_FIELDS:
            assert field in first_item, f"欄位 '{field}' 應該存在於回應中"

    def test_company_code_format(self):
        """測試公司代號格式正確."""
        data = TWSEAPIClient.get_data(self.ENDPOINT)

        for item in data[:10]:  # 檢查前 10 筆
            code = item.get("公司代號")
            assert code is not None, "公司代號不應為 None"
            assert isinstance(code, str), "公司代號應該是字串"
            assert code.isdigit(), f"公司代號應該是數字: {code}"
            assert len(code) == 4, f"公司代號應該是 4 碼: {code}"

    def test_get_company_data_by_code(self, sample_stock_code):
        """測試依公司代號查詢資料."""
        data = TWSEAPIClient.get_company_data(self.ENDPOINT, sample_stock_code)

        if data:
            assert data.get("公司代號") == sample_stock_code, \
                f"查詢結果應該是指定的公司代號 {sample_stock_code}"

    def test_revenue_data_format(self):
        """測試營收數據格式正確."""
        data = TWSEAPIClient.get_data(self.ENDPOINT)

        for item in data[:5]:
            current_revenue = item.get("營業收入-當月營收")
            # 營收應該是數字格式或包含逗號的數字字串
            if current_revenue not in ["", "N/A", None]:
                assert isinstance(current_revenue, (str, int, float)), \
                    f"營收格式不正確: {current_revenue}"