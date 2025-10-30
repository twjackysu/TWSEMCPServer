"""E2E tests for financial statements APIs."""

import pytest
from utils.api_client import TWSEAPIClient


class TestIncomeStatementAPIs:
    """綜合損益表 APIs 測試."""

    @pytest.mark.parametrize("endpoint,industry", [
        ("/opendata/t187ap06_X_basi", "金融業"),
        ("/opendata/t187ap06_X_bd", "證券期貨業"),
        ("/opendata/t187ap06_X_ci", "一般業"),
        ("/opendata/t187ap06_X_fh", "金控業"),
        ("/opendata/t187ap06_X_ins", "保險業"),
        ("/opendata/t187ap06_X_mim", "異業"),
    ])
    def test_income_statement_api_accessible(self, endpoint, industry):
        """測試綜合損益表 API 端點可訪問."""
        data = TWSEAPIClient.get_data(endpoint)
        assert data is not None, f"{industry}綜合損益表 API 應該回傳資料"
        assert isinstance(data, list), f"{industry}綜合損益表 API 應該回傳 list"
        assert len(data) > 0, f"{industry}綜合損益表 API 應該回傳至少一筆資料"

    @pytest.mark.parametrize("endpoint", [
        "/opendata/t187ap06_X_basi",
        "/opendata/t187ap06_X_bd",
        "/opendata/t187ap06_X_ci",
        "/opendata/t187ap06_X_fh",
        "/opendata/t187ap06_X_ins",
        "/opendata/t187ap06_X_mim",
    ])
    def test_income_statement_has_company_code(self, endpoint):
        """測試綜合損益表 APIs 都有公司代號欄位."""
        data = TWSEAPIClient.get_data(endpoint)
        first_item = data[0]
        # 檢查可能的公司代號欄位名稱
        assert "公司代號" in first_item or "Code" in first_item, \
            f"{endpoint} 應該包含公司代號欄位"

    def test_general_income_statement_schema(self):
        """測試一般業綜合損益表 schema."""
        endpoint = "/opendata/t187ap06_X_ci"
        data = TWSEAPIClient.get_data(endpoint)
        first_item = data[0]

        # 基本欄位檢查
        expected_basic_fields = ["公司代號", "公司名稱"]
        for field in expected_basic_fields:
            assert field in first_item, f"欄位 '{field}' 應該存在於一般業綜合損益表中"


class TestBalanceSheetAPIs:
    """資產負債表 APIs 測試."""

    @pytest.mark.parametrize("endpoint,industry", [
        ("/opendata/t187ap07_X_ci", "一般業"),
        ("/opendata/t187ap07_X_mim", "異業"),
    ])
    def test_balance_sheet_api_accessible(self, endpoint, industry):
        """測試資產負債表 API 端點可訪問."""
        data = TWSEAPIClient.get_data(endpoint)
        assert data is not None, f"{industry}資產負債表 API 應該回傳資料"
        assert isinstance(data, list), f"{industry}資產負債表 API 應該回傳 list"
        assert len(data) > 0, f"{industry}資產負債表 API 應該回傳至少一筆資料"

    @pytest.mark.parametrize("endpoint", [
        "/opendata/t187ap07_X_ci",
        "/opendata/t187ap07_X_mim",
    ])
    def test_balance_sheet_has_company_code(self, endpoint):
        """測試資產負債表 APIs 都有公司代號欄位."""
        data = TWSEAPIClient.get_data(endpoint)
        first_item = data[0]
        # 檢查可能的公司代號欄位名稱
        assert "公司代號" in first_item or "Code" in first_item, \
            f"{endpoint} 應該包含公司代號欄位"

    def test_general_balance_sheet_schema(self):
        """測試一般業資產負債表 schema."""
        endpoint = "/opendata/t187ap07_X_ci"
        data = TWSEAPIClient.get_data(endpoint)
        first_item = data[0]

        # 基本欄位檢查
        expected_basic_fields = ["公司代號", "公司名稱"]
        for field in expected_basic_fields:
            assert field in first_item, f"欄位 '{field}' 應該存在於一般業資產負債表中"


class TestFinancialDataIntegrity:
    """財務報表數據完整性測試."""

    def test_company_codes_are_valid(self):
        """測試財務報表中的公司代號格式正確."""
        # 測試一般業綜合損益表作為代表
        endpoint = "/opendata/t187ap06_X_ci"
        data = TWSEAPIClient.get_data(endpoint)

        for item in data[:10]:  # 檢查前 10 筆
            code = item.get("公司代號")
            if code and code != "N/A":  # 排除空值和 N/A
                assert isinstance(code, str), "公司代號應該是字串"
                assert code.isdigit(), f"公司代號應該是數字: {code}"
                assert len(code) == 4, f"公司代號應該是 4 碼: {code}"

    def test_financial_apis_return_consistent_company_list(self):
        """測試財務報表 APIs 回傳的公司清單基本一致."""
        # 比較一般業綜合損益表和資產負債表
        income_data = TWSEAPIClient.get_data("/opendata/t187ap06_X_ci")
        balance_data = TWSEAPIClient.get_data("/opendata/t187ap07_X_ci")

        # 提取公司代號
        income_codes = {item.get("公司代號") for item in income_data if item.get("公司代號")}
        balance_codes = {item.get("公司代號") for item in balance_data if item.get("公司代號")}

        # 應該有一定程度的重疊（至少50%）
        intersection = income_codes.intersection(balance_codes)
        min_expected_overlap = min(len(income_codes), len(balance_codes)) * 0.5

        assert len(intersection) >= min_expected_overlap, \
            f"綜合損益表和資產負債表應該有至少50%的公司重疊，實際重疊: {len(intersection)}"


class TestFinancialAPIsByCompanyCode:
    """依公司代號查詢財務報表測試."""

    def test_get_company_financial_data_by_code(self, sample_stock_code):
        """測試依公司代號查詢財務報表資料."""
        # 測試一般業綜合損益表
        income_endpoint = "/opendata/t187ap06_X_ci"
        income_data = TWSEAPIClient.get_company_data(income_endpoint, sample_stock_code)

        if income_data:
            assert income_data.get("公司代號") == sample_stock_code, \
                f"綜合損益表查詢結果應該是指定的公司代號 {sample_stock_code}"

        # 測試一般業資產負債表
        balance_endpoint = "/opendata/t187ap07_X_ci"
        balance_data = TWSEAPIClient.get_company_data(balance_endpoint, sample_stock_code)

class TestListedCompanyIncomeStatementAPIs:
    """上市公司綜合損益表 APIs 測試."""

    @pytest.mark.parametrize("endpoint,industry", [
        ("/opendata/t187ap06_L_basi", "金融業"),
        ("/opendata/t187ap06_L_bd", "證券期貨業"),
        ("/opendata/t187ap06_L_ci", "一般業"),
        ("/opendata/t187ap06_L_fh", "金控業"),
        ("/opendata/t187ap06_L_ins", "保險業"),
        ("/opendata/t187ap06_L_mim", "異業"),
    ])
    def test_listed_income_statement_api_accessible(self, endpoint, industry):
        """測試上市公司綜合損益表 API 端點可訪問."""
        data = TWSEAPIClient.get_data(endpoint)
        assert data is not None, f"{industry}上市公司綜合損益表 API 應該回傳資料"
        assert isinstance(data, list), f"{industry}上市公司綜合損益表 API 應該回傳 list"
        assert len(data) > 0, f"{industry}上市公司綜合損益表 API 應該回傳至少一筆資料"

    @pytest.mark.parametrize("endpoint", [
        "/opendata/t187ap06_L_basi",
        "/opendata/t187ap06_L_bd",
        "/opendata/t187ap06_L_ci",
        "/opendata/t187ap06_L_fh",
        "/opendata/t187ap06_L_ins",
        "/opendata/t187ap06_L_mim",
    ])
    def test_listed_income_statement_has_company_code(self, endpoint):
        """測試上市公司綜合損益表 APIs 都有公司代號欄位."""
        data = TWSEAPIClient.get_data(endpoint)
        first_item = data[0]
        # 檢查可能的公司代號欄位名稱
        assert "公司代號" in first_item or "Code" in first_item, \
            f"{endpoint} 應該包含公司代號欄位"


class TestListedCompanyBalanceSheetAPIs:
    """上市公司資產負債表 APIs 測試."""

    @pytest.mark.parametrize("endpoint,industry", [
        ("/opendata/t187ap07_L_basi", "金融業"),
        ("/opendata/t187ap07_L_bd", "證券期貨業"),
        ("/opendata/t187ap07_L_ci", "一般業"),
        ("/opendata/t187ap07_L_fh", "金控業"),
        ("/opendata/t187ap07_L_ins", "保險業"),
        ("/opendata/t187ap07_L_mim", "異業"),
    ])
    def test_listed_balance_sheet_api_accessible(self, endpoint, industry):
        """測試上市公司資產負債表 API 端點可訪問."""
        data = TWSEAPIClient.get_data(endpoint)
        assert data is not None, f"{industry}上市公司資產負債表 API 應該回傳資料"
        assert isinstance(data, list), f"{industry}上市公司資產負債表 API 應該回傳 list"
        assert len(data) > 0, f"{industry}上市公司資產負債表 API 應該回傳至少一筆資料"

    @pytest.mark.parametrize("endpoint", [
        "/opendata/t187ap07_L_basi",
        "/opendata/t187ap07_L_bd",
        "/opendata/t187ap07_L_ci",
        "/opendata/t187ap07_L_fh",
        "/opendata/t187ap07_L_ins",
        "/opendata/t187ap07_L_mim",
    ])
    def test_listed_balance_sheet_has_company_code(self, endpoint):
        """測試上市公司資產負債表 APIs 都有公司代號欄位."""
        data = TWSEAPIClient.get_data(endpoint)
        first_item = data[0]
        # 檢查可能的公司代號欄位名稱
        assert "公司代號" in first_item or "Code" in first_item, \
            f"{endpoint} 應該包含公司代號欄位"


class TestPublicCompanyBalanceSheetAPIs:
    """公發公司資產負債表 APIs 測試."""

    @pytest.mark.parametrize("endpoint,industry", [
        ("/opendata/t187ap07_X_basi", "金融業"),
        ("/opendata/t187ap07_X_bd", "證券期貨業"),
        ("/opendata/t187ap07_X_fh", "金控業"),
        ("/opendata/t187ap07_X_ins", "保險業"),
    ])
    def test_public_balance_sheet_api_accessible(self, endpoint, industry):
        """測試公發公司資產負債表 API 端點可訪問."""
        data = TWSEAPIClient.get_data(endpoint)
        assert data is not None, f"{industry}公發公司資產負債表 API 應該回傳資料"
        assert isinstance(data, list), f"{industry}公發公司資產負債表 API 應該回傳 list"
        assert len(data) > 0, f"{industry}公發公司資產負債表 API 應該回傳至少一筆資料"

    @pytest.mark.parametrize("endpoint", [
        "/opendata/t187ap07_X_basi",
        "/opendata/t187ap07_X_bd",
        "/opendata/t187ap07_X_fh",
        "/opendata/t187ap07_X_ins",
    ])
    def test_public_balance_sheet_has_company_code(self, endpoint):
        """測試公發公司資產負債表 APIs 都有公司代號欄位."""
        data = TWSEAPIClient.get_data(endpoint)
        first_item = data[0]
        # 檢查可能的公司代號欄位名稱
        assert "公司代號" in first_item or "Code" in first_item, \
            f"{endpoint} 應該包含公司代號欄位"


class TestFinancialAnalysisAPIs:
    """財務分析相關 APIs 測試."""

    @pytest.mark.parametrize("endpoint,name", [
        ("/opendata/t187ap15_L", "上市公司截至各季綜合損益財測達成情形"),
        ("/opendata/t187ap16_L", "上市公司當季綜合損益經會計師查核差異達10%以上者"),
        ("/opendata/t187ap17_L", "上市公司營益分析查詢彙總表"),
        ("/opendata/t187ap31_L", "上市公司財務報告經監察人承認情形"),
        ("/opendata/t187ap11_P", "公發公司董監事持股餘額明細"),
    ])
    def test_financial_analysis_api_accessible(self, endpoint, name):
        """測試財務分析相關 API 端點可訪問."""
        data = TWSEAPIClient.get_data(endpoint)
        assert data is not None, f"{name} API 應該回傳資料"
        assert isinstance(data, list), f"{name} API 應該回傳 list"
        assert len(data) > 0, f"{name} API 應該回傳至少一筆資料"

    def test_profitability_analysis_schema(self):
        """測試營益分析查詢彙總表 (t187ap17_L) schema."""
        endpoint = "/opendata/t187ap17_L"
        data = TWSEAPIClient.get_data(endpoint)
        first_item = data[0]

        # 檢查所有必要欄位
        expected_fields = [
            "出表日期",
            "年度",
            "季別",
            "公司代號",
            "公司名稱",
            "營業收入(百萬元)",
            "毛利率(%)(營業毛利)/(營業收入)",
            "營業利益率(%)(營業利益)/(營業收入)",
            "稅前純益率(%)(稅前純益)/(營業收入)",
            "稅後純益率(%)(稅後純益)/(營業收入)",
        ]
        
        for field in expected_fields:
            assert field in first_item, f"欄位 '{field}' 應該存在於營益分析查詢彙總表中"
        
        # 檢查數值欄位的格式
        assert isinstance(first_item["公司代號"], str), "公司代號應該是字串"
        assert first_item["公司代號"].isdigit(), "公司代號應該是數字字串"
        assert len(first_item["公司代號"]) == 4, "公司代號應該是 4 碼"