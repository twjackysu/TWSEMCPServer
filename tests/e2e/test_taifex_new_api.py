"""測試新增的 TAIFEX API 工具端點。只驗證 tool 寫死的欄位存在，不驗證動態欄位。"""

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


class TestDailyFuturesMarketReportAPI:
    """Tool get_daily_futures_market_report 寫死的欄位：
    Date, Contract, ContractMonth(Week), Open, High, Low, Last, Change, %,
    Volume, SettlementPrice, OpenInterest, BestBid, BestAsk, TradingSession
    """

    def test_hardcoded_fields_exist(self):
        data = _fetch("DailyMarketReportFut")
        assert isinstance(data, list) and len(data) > 0
        record = data[0]
        for field in [
            "Date", "Contract", "ContractMonth(Week)",
            "Open", "High", "Low", "Last", "Change", "%",
            "Volume", "SettlementPrice", "OpenInterest",
            "BestBid", "BestAsk", "TradingSession",
        ]:
            assert field in record, f"缺少欄位: {field}"

    def test_tx_contract_exists(self):
        data = _fetch("DailyMarketReportFut")
        assert any(x.get("Contract") == "TX" for x in data)


class TestDailyOptionsMarketReportAPI:
    """Tool get_daily_options_market_report 寫死的欄位：
    Date, Contract, ContractMonth(Week), StrikePrice, CallPut,
    Open, High, Low, Close, Volume, SettlementPrice, OpenInterest, TradingSession
    """

    def test_hardcoded_fields_exist(self):
        data = _fetch("DailyMarketReportOpt")
        assert isinstance(data, list) and len(data) > 0
        record = data[0]
        for field in [
            "Date", "Contract", "ContractMonth(Week)",
            "StrikePrice", "CallPut",
            "Open", "High", "Low", "Close",
            "Volume", "SettlementPrice", "OpenInterest", "TradingSession",
        ]:
            assert field in record, f"缺少欄位: {field}"

    def test_txo_contract_exists(self):
        data = _fetch("DailyMarketReportOpt")
        assert any(x.get("Contract") == "TXO" for x in data)


class TestLargeTradersOIFuturesAPI:
    """Tool get_large_traders_futures_oi 寫死的欄位：
    Date, Contract, ContractName, SettlementMonth, TypeOfTraders,
    Top5Buy, Top5Sell, Top10Buy, Top10Sell, OIOfMarket
    """

    def test_hardcoded_fields_exist(self):
        data = _fetch("OpenInterestOfLargeTradersFutures")
        assert isinstance(data, list) and len(data) > 0
        record = data[0]
        for field in [
            "Date", "Contract", "ContractName", "SettlementMonth", "TypeOfTraders",
            "Top5Buy", "Top5Sell", "Top10Buy", "Top10Sell", "OIOfMarket",
        ]:
            assert field in record, f"缺少欄位: {field}"

    def test_tx_contract_exists(self):
        data = _fetch("OpenInterestOfLargeTradersFutures")
        assert any(x.get("Contract") == "TX" for x in data)


class TestLargeTradersOIOptionsAPI:
    """Tool get_large_traders_options_oi 寫死的欄位：
    Date, Contract, ContractName, CallPut, SettlementMonth, TypeOfTraders,
    Top5Buy, Top5Sell, Top10Buy, Top10Sell, OIOfMarket
    """

    def test_hardcoded_fields_exist(self):
        data = _fetch("OpenInterestOfLargeTradersOptions")
        assert isinstance(data, list) and len(data) > 0
        record = data[0]
        for field in [
            "Date", "Contract", "ContractName", "CallPut",
            "SettlementMonth", "TypeOfTraders",
            "Top5Buy", "Top5Sell", "Top10Buy", "Top10Sell", "OIOfMarket",
        ]:
            assert field in record, f"缺少欄位: {field}"

    def test_txo_contract_exists(self):
        data = _fetch("OpenInterestOfLargeTradersOptions")
        assert any(x.get("Contract") == "TXO" for x in data)


class TestInstitutionalGeneralAPI:
    """Tool get_institutional_general 寫死的欄位：
    Date, Item,
    TradingVolume(Long/Short/Net), TradingValue(Long/Short/Net)(Millions),
    OpenInterest(Long/Short/Net),
    ContractValueOfOpenInterest(Long/Short/Net)(Millions)
    """

    def test_hardcoded_fields_exist(self):
        data = _fetch("MarketDataOfMajorInstitutionalTradersGeneralBytheDate")
        assert isinstance(data, list) and len(data) > 0
        record = data[0]
        for field in [
            "Date", "Item",
            "TradingVolume(Long)", "TradingVolume(Short)", "TradingVolume(Net)",
            "TradingValue(Long)(Millions)", "TradingValue(Short)(Millions)", "TradingValue(Net)(Millions)",
            "OpenInterest(Long)", "OpenInterest(Short)", "OpenInterest(Net)",
            "ContractValueOfOpenInterest(Long)(Millions)",
            "ContractValueOfOpenInterest(Short)(Millions)",
            "ContractValueOfOpenInterest(Net)(Millions)",
        ]:
            assert field in record, f"缺少欄位: {field}"
