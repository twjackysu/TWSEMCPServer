"""測試 tpex.org.tw/openapi 上櫃 API。只驗證 tool 會 crash 的寫死欄位。"""

from utils.api_client import TWSEAPIClient

TPEX_BASE = "https://www.tpex.org.tw/openapi/v1"


class TestOTCDailyCloseAPI:
    """Tool get_otc_daily 用 SecuritiesCompanyCode 做篩選，消失會讓篩選失效。"""

    def test_api_returns_data_with_filter_key(self):
        result = TWSEAPIClient.get_json(f"{TPEX_BASE}/tpex_mainboard_daily_close_quotes")
        assert isinstance(result, list) and len(result) > 0
        assert "SecuritiesCompanyCode" in result[0]


class TestOTCInstitutionalAPI:
    """Tool get_otc_institutional 用 SecuritiesCompanyCode 做篩選。"""

    def test_api_returns_data_with_filter_key(self):
        result = TWSEAPIClient.get_json(f"{TPEX_BASE}/tpex_3insti_daily_trading")
        assert isinstance(result, list) and len(result) > 0
        assert "SecuritiesCompanyCode" in result[0]


class TestOTCValuationAPI:
    """Tool get_otc_valuation 用 SecuritiesCompanyCode 做篩選。"""

    def test_api_returns_data_with_filter_key(self):
        result = TWSEAPIClient.get_json(f"{TPEX_BASE}/tpex_mainboard_peratio_analysis")
        assert isinstance(result, list) and len(result) > 0
        assert "SecuritiesCompanyCode" in result[0]
