"""測試第二批新增 TAIFEX API 工具端點。只驗證 tool 寫死的欄位存在。"""

import requests

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
}


def _fetch(endpoint: str) -> list:
    resp = requests.get(
        f"https://openapi.taifex.com.tw/v1/{endpoint}",
        headers=HEADERS, verify=False, timeout=15,
    )
    return resp.json()


class TestInstitutionalTradersByFuturesAPI:
    """Tool get_institutional_traders_by_futures 寫死的欄位：
    Date, ContractCode, Item,
    TradingVolume(Long/Short/Net), TradingValue(Long/Short/Net)(Thousands),
    OpenInterest(Long/Short/Net), ContractValueofOpenInterest(Long/Short/Net)(Thousands)
    """

    def test_hardcoded_fields_exist(self):
        data = _fetch("MarketDataOfMajorInstitutionalTradersDetailsOfFuturesContractsBytheDate")
        assert isinstance(data, list) and len(data) > 0
        record = data[0]
        for field in [
            "Date", "ContractCode", "Item",
            "TradingVolume(Long)", "TradingVolume(Short)", "TradingVolume(Net)",
            "TradingValue(Long)(Thousands)", "TradingValue(Short)(Thousands)", "TradingValue(Net)(Thousands)",
            "OpenInterest(Long)", "OpenInterest(Short)", "OpenInterest(Net)",
            "ContractValueofOpenInterest(Long)(Thousands)",
            "ContractValueofOpenInterest(Short)(Thousands)",
            "ContractValueofOpenInterest(Net)(Thousands)",
        ]:
            assert field in record, f"缺少欄位: {field}"


class TestInstitutionalTradersByOptionsAPI:
    """Tool get_institutional_traders_by_options 寫死的欄位：
    Date, ContractCode, Item,
    TradingVolume(Long/Short/Net), TradingValue(Long/Short/Net)(Thousands),
    OpenInterest(Long/Short/Net), ContractValueofOpenInterest(Long/Short/Net)(Thousands)
    """

    def test_hardcoded_fields_exist(self):
        data = _fetch("MarketDataOfMajorInstitutionalTradersDetailsOfOptionsContractsBytheDate")
        assert isinstance(data, list) and len(data) > 0
        record = data[0]
        for field in [
            "Date", "ContractCode", "Item",
            "TradingVolume(Long)", "TradingVolume(Short)", "TradingVolume(Net)",
            "TradingValue(Long)(Thousands)", "TradingValue(Short)(Thousands)", "TradingValue(Net)(Thousands)",
            "OpenInterest(Long)", "OpenInterest(Short)", "OpenInterest(Net)",
            "ContractValueofOpenInterest(Long)(Thousands)",
            "ContractValueofOpenInterest(Short)(Thousands)",
            "ContractValueofOpenInterest(Net)(Thousands)",
        ]:
            assert field in record, f"缺少欄位: {field}"


class TestInstitutionalTradersCallsPutsAPI:
    """Tool get_institutional_traders_calls_puts 寫死的欄位：
    Date, ContractCode, CallPut, Item,
    TradingVolume(Long/Short/Net), TradingValue(Long/Short/Net)(Thousands),
    OpenInterest(Long/Short/Net), ContractValueofOpenInterest(Long/Short/Net)(Thousands)
    """

    def test_hardcoded_fields_exist(self):
        data = _fetch("MarketDataOfMajorInstitutionalTradersDetailsOfCallsAndPutsBytheDate")
        assert isinstance(data, list) and len(data) > 0
        record = data[0]
        for field in [
            "Date", "ContractCode", "CallPut", "Item",
            "TradingVolume(Long)", "TradingVolume(Short)", "TradingVolume(Net)",
            "TradingValue(Long)(Thousands)", "TradingValue(Short)(Thousands)", "TradingValue(Net)(Thousands)",
            "OpenInterest(Long)", "OpenInterest(Short)", "OpenInterest(Net)",
            "ContractValueofOpenInterest(Long)(Thousands)",
            "ContractValueofOpenInterest(Short)(Thousands)",
            "ContractValueofOpenInterest(Net)(Thousands)",
        ]:
            assert field in record, f"缺少欄位: {field}"


class TestOptionsDeltaAPI:
    """Tool get_options_delta 寫死的欄位：
    Contract, CallPut, ContractMonth(Week), StrikePrice, Delta, ContractSettlementDay
    """

    def test_hardcoded_fields_exist(self):
        data = _fetch("DailyOptionsDelta")
        assert isinstance(data, list) and len(data) > 0
        record = data[0]
        for field in [
            "Contract", "CallPut", "ContractMonth(Week)",
            "StrikePrice", "Delta", "ContractSettlementDay",
        ]:
            assert field in record, f"缺少欄位: {field}"

    def test_txo_contract_exists(self):
        data = _fetch("DailyOptionsDelta")
        assert any(x.get("Contract") == "TXO" for x in data)


class TestOptionsOIChangeAPI:
    """Tool get_options_oi_change 寫死的欄位：
    Date, OpenInterest, PreviousDay, PreviousDayOpenInterest, Change
    """

    def test_hardcoded_fields_exist(self):
        data = _fetch("va01")
        assert isinstance(data, list) and len(data) > 0
        record = data[0]
        for field in ["Date", "OpenInterest", "PreviousDay", "PreviousDayOpenInterest", "Change"]:
            assert field in record, f"缺少欄位: {field}"


class TestIndexFuturesMarginAPI:
    """Tool get_index_futures_margin 寫死的欄位：
    Contract, ClearingMargin, MaintenanceMargin, InitialMargin, Date
    """

    def test_hardcoded_fields_exist(self):
        data = _fetch("IndexFuturesAndOptionsMargining")
        assert isinstance(data, list) and len(data) > 0
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
        assert isinstance(data, list) and len(data) > 0
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
        assert isinstance(data, list) and len(data) > 0
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
        assert isinstance(data, list) and len(data) > 0
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
