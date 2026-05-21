"""測試 tpex.org.tw/openapi 上櫃 API。只驗證 tool 會 crash 的寫死欄位。"""

from utils.api_client import TWSEAPIClient

TPEX_BASE = "https://www.tpex.org.tw/openapi/v1"


class TestOTCDailyCloseAPI:
    """Tool get_otc_daily 用 SecuritiesCompanyCode 做篩選，消失會讓篩選失效。"""

    def test_api_returns_data_with_filter_key(self):
        result = TWSEAPIClient.get_json(f"{TPEX_BASE}/tpex_mainboard_daily_close_quotes")
        assert isinstance(result, list) and len(result) > 0
        assert "SecuritiesCompanyCode" in result[0]

    def test_hardcoded_fields_exist(self):
        result = TWSEAPIClient.get_json(f"{TPEX_BASE}/tpex_mainboard_daily_close_quotes")
        assert isinstance(result, list) and len(result) > 0
        first = result[0]
        required = ["SecuritiesCompanyCode", "CompanyName", "Close", "Change", "Open", "High", "Low", "TradingShares"]
        missing = [f for f in required if f not in first]
        assert not missing, (
            f"tpex_mainboard_daily_close_quotes removed fields that get_otc_daily uses.\n"
            f"Missing: {missing}\n"
            f"Actual fields: {sorted(first.keys())}"
        )


class TestOTCInstitutionalAPI:
    """Tool get_otc_institutional 用 SecuritiesCompanyCode 做篩選。"""

    def test_api_returns_data_with_filter_key(self):
        result = TWSEAPIClient.get_json(f"{TPEX_BASE}/tpex_3insti_daily_trading")
        assert isinstance(result, list) and len(result) > 0
        assert "SecuritiesCompanyCode" in result[0]

    def test_hardcoded_fields_exist(self):
        result = TWSEAPIClient.get_json(f"{TPEX_BASE}/tpex_3insti_daily_trading")
        assert isinstance(result, list) and len(result) > 0
        first = result[0]
        required = [
            "SecuritiesCompanyCode",
            "CompanyName",
            "ForeignInvestorsInclude MainlandAreaInvestors-Difference",
            "SecuritiesInvestmentTrustCompanies-Difference",
            "Dealers-Difference",
            "TotalDifference",
        ]
        missing = [f for f in required if f not in first]
        assert not missing, (
            f"tpex_3insti_daily_trading removed fields that get_otc_institutional uses.\n"
            f"Missing: {missing}\n"
            f"Actual fields: {sorted(first.keys())}"
        )


class TestOTCValuationAPI:
    """Tool get_otc_valuation 用 SecuritiesCompanyCode 做篩選。"""

    def test_api_returns_data_with_filter_key(self):
        result = TWSEAPIClient.get_json(f"{TPEX_BASE}/tpex_mainboard_peratio_analysis")
        assert isinstance(result, list) and len(result) > 0
        assert "SecuritiesCompanyCode" in result[0]

    def test_hardcoded_fields_exist(self):
        result = TWSEAPIClient.get_json(f"{TPEX_BASE}/tpex_mainboard_peratio_analysis")
        assert isinstance(result, list) and len(result) > 0
        first = result[0]
        # YieldRatio or DividendYield — tool tries YieldRatio first, falls back to DividendYield
        has_yield = "YieldRatio" in first or "DividendYield" in first
        required_base = ["SecuritiesCompanyCode", "CompanyName", "PriceEarningRatio", "PriceBookRatio"]
        missing = [f for f in required_base if f not in first]
        assert not missing and has_yield, (
            f"tpex_mainboard_peratio_analysis removed fields that get_otc_valuation uses.\n"
            f"Missing base fields: {missing}\n"
            f"YieldRatio present: {'YieldRatio' in first}, DividendYield present: {'DividendYield' in first}\n"
            f"Actual fields: {sorted(first.keys())}"
        )
