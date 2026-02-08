"""E2E tests for financial statements APIs.

測試策略：
1. 每個 API endpoint 只測試一次
2. 只測試 tool 層「寫死」的欄位（明確在程式碼中指定的欄位名稱）
3. 使用 format_properties_with_values_multiline 的 API 不算寫死，只需確認有資料即可
4. rate limiting 由 conftest.py 的 autouse fixture 統一處理

Tool 層寫死的欄位：
- _get_industry_api_suffix: 使用 "產業別" (from t187ap03_L)
- get_company_profitability_analysis_summary: 使用 10 個特定欄位 (from t187ap17_L)
- 其他所有 tools 使用 format_properties_with_values_multiline，動態處理所有欄位
"""

import pytest
from utils.api_client import TWSEAPIClient


# ============================================================================
# Listed Company Income Statements (上市公司綜合損益表) - t187ap06_L_*
# Tool: get_company_income_statement 使用 format_properties_with_values_multiline (不寫死欄位)
# ============================================================================

class TestListedCompanyIncomeStatements:
    """上市公司綜合損益表 API 可用性測試."""

    def test_t187ap06_L_basi_available(self):
        """測試金融業綜合損益表 API 可用."""
        data = TWSEAPIClient.get_data("/opendata/t187ap06_L_basi")
        if not data:
            pytest.skip("API 目前返回空資料")
        assert isinstance(data, list) and len(data) > 0

    def test_t187ap06_L_bd_available(self):
        """測試證券期貨業綜合損益表 API 可用."""
        data = TWSEAPIClient.get_data("/opendata/t187ap06_L_bd")
        if not data:
            pytest.skip("API 目前返回空資料")
        assert isinstance(data, list) and len(data) > 0

    def test_t187ap06_L_ci_available(self):
        """測試一般業綜合損益表 API 可用."""
        data = TWSEAPIClient.get_data("/opendata/t187ap06_L_ci")
        if not data:
            pytest.skip("API 目前返回空資料")
        assert isinstance(data, list) and len(data) > 0

    def test_t187ap06_L_fh_available(self):
        """測試金控業綜合損益表 API 可用."""
        data = TWSEAPIClient.get_data("/opendata/t187ap06_L_fh")
        if not data:
            pytest.skip("API 目前返回空資料")
        assert isinstance(data, list) and len(data) > 0

    def test_t187ap06_L_ins_available(self):
        """測試保險業綜合損益表 API 可用."""
        data = TWSEAPIClient.get_data("/opendata/t187ap06_L_ins")
        if not data:
            pytest.skip("API 目前返回空資料")
        assert isinstance(data, list) and len(data) > 0

    def test_t187ap06_L_mim_available(self):
        """測試異業綜合損益表 API 可用."""
        data = TWSEAPIClient.get_data("/opendata/t187ap06_L_mim")
        if not data:
            pytest.skip("API 目前返回空資料")
        assert isinstance(data, list) and len(data) > 0


# ============================================================================
# Listed Company Balance Sheets (上市公司資產負債表) - t187ap07_L_*
# Tool: get_company_balance_sheet 使用 format_properties_with_values_multiline (不寫死欄位)
# ============================================================================

class TestListedCompanyBalanceSheets:
    """上市公司資產負債表 API 可用性測試."""

    def test_t187ap07_L_basi_available(self):
        """測試金融業資產負債表 API 可用."""
        data = TWSEAPIClient.get_data("/opendata/t187ap07_L_basi")
        if not data:
            pytest.skip("API 目前返回空資料")
        assert isinstance(data, list) and len(data) > 0

    def test_t187ap07_L_bd_available(self):
        """測試證券期貨業資產負債表 API 可用."""
        data = TWSEAPIClient.get_data("/opendata/t187ap07_L_bd")
        if not data:
            pytest.skip("API 目前返回空資料")
        assert isinstance(data, list) and len(data) > 0

    def test_t187ap07_L_ci_available(self):
        """測試一般業資產負債表 API 可用."""
        data = TWSEAPIClient.get_data("/opendata/t187ap07_L_ci")
        if not data:
            pytest.skip("API 目前返回空資料")
        assert isinstance(data, list) and len(data) > 0

    def test_t187ap07_L_fh_available(self):
        """測試金控業資產負債表 API 可用."""
        data = TWSEAPIClient.get_data("/opendata/t187ap07_L_fh")
        if not data:
            pytest.skip("API 目前返回空資料")
        assert isinstance(data, list) and len(data) > 0

    def test_t187ap07_L_ins_available(self):
        """測試保險業資產負債表 API 可用."""
        data = TWSEAPIClient.get_data("/opendata/t187ap07_L_ins")
        if not data:
            pytest.skip("API 目前返回空資料")
        assert isinstance(data, list) and len(data) > 0

    def test_t187ap07_L_mim_available(self):
        """測試異業資產負債表 API 可用."""
        data = TWSEAPIClient.get_data("/opendata/t187ap07_L_mim")
        if not data:
            pytest.skip("API 目前返回空資料")
        assert isinstance(data, list) and len(data) > 0


# ============================================================================
# Public Company Income Statements (公發公司綜合損益表) - t187ap06_X_*
# Tool: get_public_company_income_statement 使用 format_properties_with_values_multiline (不寫死欄位)
# ============================================================================

class TestPublicCompanyIncomeStatements:
    """公發公司綜合損益表 API 可用性測試."""

    def test_t187ap06_X_basi_available(self):
        """測試金融業綜合損益表 API 可用."""
        data = TWSEAPIClient.get_data("/opendata/t187ap06_X_basi")
        if not data:
            pytest.skip("API 目前返回空資料")
        assert isinstance(data, list) and len(data) > 0

    def test_t187ap06_X_bd_available(self):
        """測試證券期貨業綜合損益表 API 可用."""
        data = TWSEAPIClient.get_data("/opendata/t187ap06_X_bd")
        if not data:
            pytest.skip("API 目前返回空資料")
        assert isinstance(data, list) and len(data) > 0

    def test_t187ap06_X_ci_available(self):
        """測試一般業綜合損益表 API 可用."""
        data = TWSEAPIClient.get_data("/opendata/t187ap06_X_ci")
        if not data:
            pytest.skip("API 目前返回空資料")
        assert isinstance(data, list) and len(data) > 0

    def test_t187ap06_X_fh_available(self):
        """測試金控業綜合損益表 API 可用."""
        data = TWSEAPIClient.get_data("/opendata/t187ap06_X_fh")
        if not data:
            pytest.skip("API 目前返回空資料")
        assert isinstance(data, list) and len(data) > 0

    def test_t187ap06_X_ins_available(self):
        """測試保險業綜合損益表 API 可用."""
        data = TWSEAPIClient.get_data("/opendata/t187ap06_X_ins")
        if not data:
            pytest.skip("API 目前返回空資料")
        assert isinstance(data, list) and len(data) > 0

    def test_t187ap06_X_mim_available(self):
        """測試異業綜合損益表 API 可用."""
        data = TWSEAPIClient.get_data("/opendata/t187ap06_X_mim")
        if not data:
            pytest.skip("API 目前返回空資料")
        assert isinstance(data, list) and len(data) > 0


# ============================================================================
# Public Company Balance Sheets (公發公司資產負債表) - t187ap07_X_*
# Tool: get_public_company_balance_sheet 使用 format_properties_with_values_multiline (不寫死欄位)
# ============================================================================

class TestPublicCompanyBalanceSheets:
    """公發公司資產負債表 API 可用性測試."""

    def test_t187ap07_X_basi_available(self):
        """測試金融業資產負債表 API 可用."""
        data = TWSEAPIClient.get_data("/opendata/t187ap07_X_basi")
        if not data:
            pytest.skip("API 目前返回空資料")
        assert isinstance(data, list) and len(data) > 0

    def test_t187ap07_X_bd_available(self):
        """測試證券期貨業資產負債表 API 可用."""
        data = TWSEAPIClient.get_data("/opendata/t187ap07_X_bd")
        if not data:
            pytest.skip("API 目前返回空資料")
        assert isinstance(data, list) and len(data) > 0

    def test_t187ap07_X_ci_available(self):
        """測試一般業資產負債表 API 可用."""
        data = TWSEAPIClient.get_data("/opendata/t187ap07_X_ci")
        if not data:
            pytest.skip("API 目前返回空資料")
        assert isinstance(data, list) and len(data) > 0

    def test_t187ap07_X_fh_available(self):
        """測試金控業資產負債表 API 可用."""
        data = TWSEAPIClient.get_data("/opendata/t187ap07_X_fh")
        if not data:
            pytest.skip("API 目前返回空資料")
        assert isinstance(data, list) and len(data) > 0

    def test_t187ap07_X_ins_available(self):
        """測試保險業資產負債表 API 可用."""
        data = TWSEAPIClient.get_data("/opendata/t187ap07_X_ins")
        if not data:
            pytest.skip("API 目前返回空資料")
        assert isinstance(data, list) and len(data) > 0

    def test_t187ap07_X_mim_available(self):
        """測試異業資產負債表 API 可用."""
        data = TWSEAPIClient.get_data("/opendata/t187ap07_X_mim")
        if not data:
            pytest.skip("API 目前返回空資料")
        assert isinstance(data, list) and len(data) > 0


# ============================================================================
# Other Financial Reports (其他財務報表)
# ============================================================================

class TestOtherFinancialReports:
    """其他財務報表 API 測試."""

    def test_t187ap15_L_available(self):
        """測試季營業額預估達成情形(簡式) - t187ap15_L.
        
        Tool: get_company_quarterly_earnings_forecast_achievement
        使用 format_properties_with_values_multiline (不寫死欄位)
        """
        data = TWSEAPIClient.get_data("/opendata/t187ap15_L")
        if not data:
            pytest.skip("API 目前返回空資料")
        assert isinstance(data, list) and len(data) > 0

    def test_t187ap16_L_available(self):
        """測試季綜合損益表經會計師核閱或查核與預估差異達百分之十以上 - t187ap16_L.
        
        Tool: get_company_quarterly_audit_variance
        使用 format_properties_with_values_multiline (不寫死欄位)
        """
        data = TWSEAPIClient.get_data("/opendata/t187ap16_L")
        if not data:
            pytest.skip("API 目前返回空資料")
        assert isinstance(data, list) and len(data) > 0

    def test_t187ap17_L_schema(self):
        """測試營益分析查詢彙總表 - t187ap17_L.
        
        Tool: get_company_profitability_analysis_summary
        此 API 在 tool 層有寫死使用以下欄位，需要全部測試
        """
        data = TWSEAPIClient.get_data("/opendata/t187ap17_L")
        if not data:
            pytest.skip("API 目前返回空資料")
        
        # 這些欄位在 tools/company/financials.py 中被寫死使用
        required_fields = [
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
        
        for field in required_fields:
            assert field in data[0], f"欄位 '{field}' 應該存在於營益分析查詢彙總表中"

    def test_t187ap31_L_available(self):
        """測試財務報表經監察人(或審計委員會)承認 - t187ap31_L.
        
        Tool: get_company_financial_reports_supervisor_acknowledgment
        使用 format_properties_with_values_multiline (不寫死欄位)
        """
        data = TWSEAPIClient.get_data("/opendata/t187ap31_L")
        if not data:
            pytest.skip("API 目前返回空資料")
        assert isinstance(data, list) and len(data) > 0

    def test_t187ap11_P_available(self):
        """測試公開發行公司董監事股票設質明細 - t187ap11_P.
        
        Tool: get_public_company_board_shareholdings
        使用 format_properties_with_values_multiline (不寫死欄位)
        """
        data = TWSEAPIClient.get_data("/opendata/t187ap11_P")
        if not data:
            pytest.skip("API 目前返回空資料")
        assert isinstance(data, list) and len(data) > 0