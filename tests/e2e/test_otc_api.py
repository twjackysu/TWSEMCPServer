"""測試 tpex.org.tw/openapi 上櫃 API。只驗證 tool 會 crash 的寫死欄位。"""

import pytest
from tests.helpers import fetch_or_skip

TPEX_BASE = "https://www.tpex.org.tw/openapi/v1"


class TestOTCDailyCloseAPI:
    """Tool get_otc_daily 用 SecuritiesCompanyCode 做篩選，消失會讓篩選失效。"""

    def test_hardcoded_fields_exist(self):
        result = fetch_or_skip(f"{TPEX_BASE}/tpex_mainboard_daily_close_quotes")
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

    def test_hardcoded_fields_exist(self):
        result = fetch_or_skip(f"{TPEX_BASE}/tpex_3insti_daily_trading")
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

    def test_hardcoded_fields_exist(self):
        result = fetch_or_skip(f"{TPEX_BASE}/tpex_mainboard_peratio_analysis")
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


class TestOTCMarginBalanceAPI:
    """Tool get_otc_margin_balance 用 SecuritiesCompanyCode 篩選，3 個數值欄位顯示。"""

    def test_hardcoded_fields_exist(self):
        result = fetch_or_skip(f"{TPEX_BASE}/tpex_mainboard_margin_balance")
        assert isinstance(result, list) and len(result) > 0
        first = result[0]
        required = [
            "SecuritiesCompanyCode", "CompanyName",
            "MarginPurchaseBalance", "ShortSaleBalance", "MarginPurchaseUtilizationRate",
        ]
        missing = [f for f in required if f not in first]
        assert not missing, (
            f"tpex_mainboard_margin_balance removed fields that get_otc_margin_balance uses.\n"
            f"Missing: {missing}\nActual fields: {sorted(first.keys())}"
        )


class TestOTCTradingWarningAPI:
    """Tool get_otc_warning_stocks 顯示注意事由與收盤價。"""

    def test_hardcoded_fields_exist(self):
        result = fetch_or_skip(f"{TPEX_BASE}/tpex_trading_warning_information")
        assert isinstance(result, list) and len(result) > 0
        first = result[0]
        required = ["SecuritiesCompanyCode", "CompanyName", "TradingInformation", "ClosePrice"]
        missing = [f for f in required if f not in first]
        assert not missing, (
            f"tpex_trading_warning_information removed fields that get_otc_warning_stocks uses.\n"
            f"Missing: {missing}\nActual fields: {sorted(first.keys())}"
        )


class TestOTCDisposalAPI:
    """Tool get_otc_disposal_stocks 顯示處置期間與原因。"""

    def test_hardcoded_fields_exist(self):
        result = fetch_or_skip(f"{TPEX_BASE}/tpex_disposal_information")
        assert isinstance(result, list) and len(result) > 0
        first = result[0]
        required = ["SecuritiesCompanyCode", "CompanyName", "DispositionPeriod", "DispositionReasons"]
        missing = [f for f in required if f not in first]
        assert not missing, (
            f"tpex_disposal_information removed fields that get_otc_disposal_stocks uses.\n"
            f"Missing: {missing}\nActual fields: {sorted(first.keys())}"
        )


class TestOTCExrightAPI:
    """Tool get_otc_exright 顯示除權息各欄位。"""

    def test_hardcoded_fields_exist(self):
        result = fetch_or_skip(f"{TPEX_BASE}/tpex_exright_daily")
        # May be empty on non-trading or non-exright days — skip rather than fail
        if not isinstance(result, list) or not result:
            pytest.skip("tpex_exright_daily returned no data today (no ex-rights/dividends)")
        first = result[0]
        required = [
            "SecuritiesCompanyCode", "CompanyName",
            "ClosePriceBeforeExRightsDiviend", "ExRightsDiviendQuote",
            "StockDividend", "CashDividend", "ExRightsDiviend",
        ]
        missing = [f for f in required if f not in first]
        assert not missing, (
            f"tpex_exright_daily removed fields that get_otc_exright uses.\n"
            f"Missing: {missing}\nActual fields: {sorted(first.keys())}"
        )


class TestOTCOddLotAPI:
    """Tool get_otc_odd_lot 顯示零股價格與成交資料。"""

    def test_hardcoded_fields_exist(self):
        result = fetch_or_skip(f"{TPEX_BASE}/tpex_odd_stock")
        assert isinstance(result, list) and len(result) > 0
        first = result[0]
        required = ["SecuritiesCompanyCode", "CompanyName", "TradeVolume", "Price", "TradeAmount"]
        missing = [f for f in required if f not in first]
        assert not missing, (
            f"tpex_odd_stock removed fields that get_otc_odd_lot uses.\n"
            f"Missing: {missing}\nActual fields: {sorted(first.keys())}"
        )


class TestOTCIndexAPI:
    """Tool get_otc_index 顯示開高低收漲跌。"""

    def test_hardcoded_fields_exist(self):
        result = fetch_or_skip(f"{TPEX_BASE}/tpex_index")
        assert isinstance(result, list) and len(result) > 0
        first = result[0]
        required = ["Date", "Open", "High", "Low", "Close", "Change"]
        missing = [f for f in required if f not in first]
        assert not missing, (
            f"tpex_index removed fields that get_otc_index uses.\n"
            f"Missing: {missing}\nActual fields: {sorted(first.keys())}"
        )


class TestOTCInstitutionalSummaryAPI:
    """Tool get_otc_institutional_summary 顯示三大法人彙總買賣超。"""

    def test_hardcoded_fields_exist(self):
        result = fetch_or_skip(f"{TPEX_BASE}/tpex_3insti_summary")
        assert isinstance(result, list) and len(result) > 0
        first = result[0]
        required = ["Date", "Investor", "PurchaseAmount", "SaleAmount", "Net"]
        missing = [f for f in required if f not in first]
        assert not missing, (
            f"tpex_3insti_summary removed fields that get_otc_institutional_summary uses.\n"
            f"Missing: {missing}\nActual fields: {sorted(first.keys())}"
        )
