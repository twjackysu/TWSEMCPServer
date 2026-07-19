"""測試新增的 TAIFEX API 工具端點。只驗證 tool 寫死的欄位存在，不驗證動態欄位。"""

import pytest
from tests.helpers import fetch_or_skip

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
}


def _fetch(endpoint: str) -> list:
    return fetch_or_skip(
        f"https://openapi.taifex.com.tw/v1/{endpoint}",
        headers=HEADERS, timeout=15,
    )


@pytest.fixture(scope="class")
def daily_market_report_fut():
    return _fetch("DailyMarketReportFut")


class TestDailyFuturesMarketReportAPI:
    """Tool get_daily_futures_market_report 寫死的欄位：
    Date, Contract, ContractMonth(Week), Open, High, Low, Last, Change, %,
    Volume, SettlementPrice, OpenInterest, BestBid, BestAsk, TradingSession
    """

    def test_hardcoded_fields_exist(self, daily_market_report_fut):
        assert isinstance(daily_market_report_fut, list) and len(daily_market_report_fut) > 0
        record = daily_market_report_fut[0]
        for field in [
            "Date", "Contract", "ContractMonth(Week)",
            "Open", "High", "Low", "Last", "Change", "%",
            "Volume", "SettlementPrice", "OpenInterest",
            "BestBid", "BestAsk", "TradingSession",
        ]:
            assert field in record, f"缺少欄位: {field}"

    def test_tx_contract_exists(self, daily_market_report_fut):
        assert any(x.get("Contract") == "TX" for x in daily_market_report_fut)


@pytest.fixture(scope="class")
def daily_market_report_opt():
    return _fetch("DailyMarketReportOpt")


class TestDailyOptionsMarketReportAPI:
    """Tool get_daily_options_market_report 寫死的欄位：
    Date, Contract, ContractMonth(Week), StrikePrice, CallPut,
    Open, High, Low, Close, Volume, SettlementPrice, OpenInterest, TradingSession
    """

    def test_hardcoded_fields_exist(self, daily_market_report_opt):
        assert isinstance(daily_market_report_opt, list) and len(daily_market_report_opt) > 0
        record = daily_market_report_opt[0]
        for field in [
            "Date", "Contract", "ContractMonth(Week)",
            "StrikePrice", "CallPut",
            "Open", "High", "Low", "Close",
            "Volume", "SettlementPrice", "OpenInterest", "TradingSession",
        ]:
            assert field in record, f"缺少欄位: {field}"

    def test_txo_contract_exists(self, daily_market_report_opt):
        assert any(x.get("Contract") == "TXO" for x in daily_market_report_opt)


def _fetch_large_traders_oi_futures() -> list:
    """OpenInterestOfLargeTradersFutures started returning CSV instead of JSON as of
    2026-07 (confirmed genuine upstream regression, not a header/format issue on our
    side — the sibling Options endpoint is unaffected). Tool get_large_traders_futures_oi
    tolerates this via a JSON-with-CSV-fallback helper; mirror that here so this test
    keeps validating the fields the tool actually depends on regardless of which format
    the API happens to be serving.
    """
    resp = requests.get(
        "https://openapi.taifex.com.tw/v1/OpenInterestOfLargeTradersFutures",
        headers=HEADERS, verify=False, timeout=15,
    )
    try:
        return resp.json()
    except requests.exceptions.JSONDecodeError:
        pass

    import csv
    import io

    header_map = {
        "日期": "Date", "契約": "Contract", "商品名稱(契約名稱)": "ContractName",
        "到期月份(週別)": "SettlementMonth", "交易人類別": "TypeOfTraders",
        "前五大交易人買方數量": "Top5Buy", "前五大交易人賣方數量": "Top5Sell",
        "前十大交易人買方數量": "Top10Buy", "前十大交易人賣方數量": "Top10Sell",
        "全市場未沖銷部位數": "OIOfMarket",
    }
    rows = list(csv.reader(io.StringIO(resp.content.decode("utf-8-sig", errors="replace"))))
    header = [header_map.get(h.strip(), h.strip()) for h in rows[0]]
    return [dict(zip(header, r)) for r in rows[1:] if r and r[0].strip()]


@pytest.fixture(scope="class")
def large_traders_oi_futures():
    return _fetch_large_traders_oi_futures()


class TestLargeTradersOIFuturesAPI:
    """Tool get_large_traders_futures_oi 寫死的欄位：
    Date, Contract, ContractName, SettlementMonth, TypeOfTraders,
    Top5Buy, Top5Sell, Top10Buy, Top10Sell, OIOfMarket
    """

    def test_hardcoded_fields_exist(self, large_traders_oi_futures):
        assert isinstance(large_traders_oi_futures, list) and len(large_traders_oi_futures) > 0
        record = large_traders_oi_futures[0]
        for field in [
            "Date", "Contract", "ContractName", "SettlementMonth", "TypeOfTraders",
            "Top5Buy", "Top5Sell", "Top10Buy", "Top10Sell", "OIOfMarket",
        ]:
            assert field in record, f"缺少欄位: {field}"

    def test_tx_contract_exists(self, large_traders_oi_futures):
        assert any(x.get("Contract") == "TX" for x in large_traders_oi_futures)


@pytest.fixture(scope="class")
def large_traders_oi_options():
    return _fetch("OpenInterestOfLargeTradersOptions")


class TestLargeTradersOIOptionsAPI:
    """Tool get_large_traders_options_oi 寫死的欄位：
    Date, Contract, ContractName, CallPut, SettlementMonth, TypeOfTraders,
    Top5Buy, Top5Sell, Top10Buy, Top10Sell, OIOfMarket
    """

    def test_hardcoded_fields_exist(self, large_traders_oi_options):
        assert isinstance(large_traders_oi_options, list) and len(large_traders_oi_options) > 0
        record = large_traders_oi_options[0]
        for field in [
            "Date", "Contract", "ContractName", "CallPut",
            "SettlementMonth", "TypeOfTraders",
            "Top5Buy", "Top5Sell", "Top10Buy", "Top10Sell", "OIOfMarket",
        ]:
            assert field in record, f"缺少欄位: {field}"

    def test_txo_contract_exists(self, large_traders_oi_options):
        assert any(x.get("Contract") == "TXO" for x in large_traders_oi_options)


@pytest.fixture(scope="class")
def daily_options_delta():
    return _fetch("DailyOptionsDelta")


class TestOptionsDeltaAPI:
    """Tool get_options_delta 寫死的欄位：
    Contract, CallPut, ContractMonth(Week), StrikePrice, Delta, ContractSettlementDay
    """

    def test_hardcoded_fields_exist(self, daily_options_delta):
        assert isinstance(daily_options_delta, list) and len(daily_options_delta) > 0
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
