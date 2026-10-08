"""測試新增的 TAIFEX API 工具端點。只驗證 tool 寫死的欄位存在，不驗證動態欄位。"""

import pytest
from tests.helpers import fetch_or_skip, records_or_skip

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
}


def _fetch(endpoint: str) -> list:
    return records_or_skip(
        fetch_or_skip(f"https://openapi.taifex.com.tw/v1/{endpoint}", headers=HEADERS, timeout=15),
        endpoint,
    )


@pytest.fixture(scope="class")
def daily_options_delta():
    return _fetch("DailyOptionsDelta")


class TestOptionsDeltaAPI:
    """Tool get_options_delta 寫死的欄位：
    Contract, CallPut, ContractMonth(Week), StrikePrice, Delta, ContractSettlementDay
    """

    def test_hardcoded_fields_exist(self, daily_options_delta):
        record = daily_options_delta[0]
        for field in [
            "Contract", "CallPut", "ContractMonth(Week)",
            "StrikePrice", "Delta", "ContractSettlementDay",
        ]:
            assert field in record, f"缺少欄位: {field}"

    def test_txo_contract_exists(self, daily_options_delta):
        assert any(x.get("Contract") == "TXO" for x in daily_options_delta)


class TestOptionsOIChangeAPI:
    """Tool get_options_oi_change 寫死的欄位：
    Date, OpenInterest, PreviousDay, PreviousDayOpenInterest, Change
    """

    def test_hardcoded_fields_exist(self):
        data = _fetch("va01")
        record = data[0]
        for field in ["Date", "OpenInterest", "PreviousDay", "PreviousDayOpenInterest", "Change"]:
            assert field in record, f"缺少欄位: {field}"


class TestIndexFuturesMarginAPI:
    """Tool get_index_futures_margin 寫死的欄位：
    Contract, ClearingMargin, MaintenanceMargin, InitialMargin, Date
    """

    def test_hardcoded_fields_exist(self):
        data = _fetch("IndexFuturesAndOptionsMargining")
        record = data[0]
        for field in ["Contract", "ClearingMargin", "MaintenanceMargin", "InitialMargin", "Date"]:
            assert field in record, f"缺少欄位: {field}"


class TestStockFuturesMarginAPI:
    """Tool get_stock_futures_margin 寫死的欄位：
    Contract, UnderlyingSecurityCode, ContractName, GroupLevel,
    ClearingMarginRate, MaintenanceMarginRate, InitialMarginRate, Date
    """

    def test_hardcoded_fields_exist(self):
        data = _fetch("SingleStockFuturesMargining")
        record = data[0]
        for field in [
            "Contract", "UnderlyingSecurityCode", "ContractName",
            "GroupLevel", "ClearingMarginRate", "MaintenanceMarginRate",
            "InitialMarginRate", "Date",
        ]:
            assert field in record, f"缺少欄位: {field}"


class TestAnnualTradingVolumeAPI:
    """Tool get_annual_trading_volume 寫死的欄位：
    YYYY, Contract, ContractName, Volume, NumberOfTradingDays, AvgDailyTradingVolume
    """

    def test_hardcoded_fields_exist(self):
        data = _fetch("AnnualTradingVolume")
        record = data[0]
        for field in [
            "YYYY", "Contract", "ContractName",
            "Volume", "NumberOfTradingDays", "AvgDailyTradingVolume",
        ]:
            assert field in record, f"缺少欄位: {field}"


class TestMonthlyTradingStatisticsAPI:
    """Tool get_monthly_trading_statistics 寫死的欄位：
    YYYYMM, ContactName, TotalVolume, MonthEndOpenInterest,
    Brokers-Individual(Buy/Sell), ProprietaryTraders(Buy/Sell),
    Brokers-InstutionalInvestors-SecuritiesInvestmentTrust(Buy/Sell),
    Brokers-InstutionalInvestors-Foreign&MainlandAreaInstitutionalInvestors(Buy/Sell),
    Brokers-InstutionalInvestors-SecuritiesDealers(Buy/Sell)
    """

    def test_hardcoded_fields_exist(self):
        data = _fetch("MonthlyTradingStatisticsFutures")
        record = data[0]
        for field in [
            "YYYYMM", "ContactName", "TotalVolume", "MonthEndOpenInterest",
            "Brokers-Individual(Buy)", "Brokers-Individual(Sell)",
            "ProprietaryTraders(Buy)", "ProprietaryTraders(Sell)",
            "Brokers-InstutionalInvestors-SecuritiesInvestmentTrust(Buy)",
            "Brokers-InstutionalInvestors-SecuritiesInvestmentTrust(Sell)",
            "Brokers-InstutionalInvestors-Foreign&MainlandAreaInstitutionalInvestors(Buy)",
            "Brokers-InstutionalInvestors-Foreign&MainlandAreaInstitutionalInvestors(Sell)",
            "Brokers-InstutionalInvestors-SecuritiesDealers(Buy)",
            "Brokers-InstutionalInvestors-SecuritiesDealers(Sell)",
        ]:
            assert field in record, f"缺少欄位: {field}"
