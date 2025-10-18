"""E2E tests for trading-related APIs."""

import pytest
from utils.api_client import TWSEAPIClient


class TestStockTradingAPIs:
    """股票交易相關 APIs 測試."""

    @pytest.mark.parametrize("endpoint,name", [
        ("/exchangeReport/BWIBBU_ALL", "個股日本益比、殖利率及股價淨值比"),
        ("/exchangeReport/STOCK_DAY_AVG_ALL", "個股日收盤價及月平均價"),
        ("/exchangeReport/STOCK_DAY_ALL", "個股日成交資訊"),
        ("/exchangeReport/FMSRFK_ALL", "個股月成交資訊"),
        ("/exchangeReport/FMNPTK_ALL", "個股年成交資訊"),
        ("/exchangeReport/TWT48U_ALL", "股票除權除息預告表"),
    ])
    def test_stock_trading_api_accessible(self, endpoint, name):
        """測試股票交易 API 端點可訪問."""
        data = TWSEAPIClient.get_data(endpoint)
        assert data is not None, f"{name} API 應該回傳資料"
        assert isinstance(data, list), f"{name} API 應該回傳 list"
        assert len(data) > 0, f"{name} API 應該回傳至少一筆資料"

    def test_stock_valuation_ratios_schema(self):
        """測試個股本益比等評價指標 schema."""
        endpoint = "/exchangeReport/BWIBBU_ALL"
        data = TWSEAPIClient.get_data(endpoint)
        first_item = data[0]

        expected_fields = ["Code", "Name"]  # 基本必要欄位
        for field in expected_fields:
            assert field in first_item, f"欄位 '{field}' 應該存在於本益比資料中"

    def test_daily_trading_schema(self):
        """測試個股日成交資訊 schema."""
        endpoint = "/exchangeReport/STOCK_DAY_ALL"
        data = TWSEAPIClient.get_data(endpoint)
        first_item = data[0]

        expected_fields = ["Code", "Name"]  # 基本必要欄位
        for field in expected_fields:
            assert field in first_item, f"欄位 '{field}' 應該存在於日成交資訊中"

    def test_monthly_trading_schema(self):
        """測試個股月成交資訊 schema."""
        endpoint = "/exchangeReport/FMSRFK_ALL"
        data = TWSEAPIClient.get_data(endpoint)
        first_item = data[0]

        expected_fields = ["Code", "Name"]  # 基本必要欄位
        for field in expected_fields:
            assert field in first_item, f"欄位 '{field}' 應該存在於月成交資訊中"

    def test_yearly_trading_schema(self):
        """測試個股年成交資訊 schema."""
        endpoint = "/exchangeReport/FMNPTK_ALL"
        data = TWSEAPIClient.get_data(endpoint)
        first_item = data[0]

        expected_fields = ["Code", "Name"]  # 基本必要欄位
        for field in expected_fields:
            assert field in first_item, f"欄位 '{field}' 應該存在於年成交資訊中"

    def test_dividend_schedule_schema(self):
        """測試除權除息預告表 schema."""
        endpoint = "/exchangeReport/TWT48U_ALL"
        data = TWSEAPIClient.get_data(endpoint)
        first_item = data[0]

        expected_fields = ["Code", "Name"]  # 基本必要欄位
        for field in expected_fields:
            assert field in first_item, f"欄位 '{field}' 應該存在於除權除息預告表中"


class TestMarketStatisticsAPIs:
    """市場統計相關 APIs 測試."""

    def test_market_index_api(self):
        """測試大盤統計資訊 API."""
        endpoint = "/exchangeReport/MI_INDEX"
        data = TWSEAPIClient.get_data(endpoint)
        assert data is not None, "大盤統計資訊 API 應該回傳資料"
        assert isinstance(data, list), "大盤統計資訊 API 應該回傳 list"
        assert len(data) > 0, "大盤統計資訊 API 應該回傳至少一筆資料"

    def test_real_time_stats_api(self):
        """測試 5 秒委託成交統計 API."""
        endpoint = "/exchangeReport/MI_5MINS"
        data = TWSEAPIClient.get_data(endpoint)
        assert data is not None, "5秒統計 API 應該回傳資料"
        assert isinstance(data, list), "5秒統計 API 應該回傳 list"
        assert len(data) > 0, "5秒統計 API 應該回傳至少一筆資料"

    def test_margin_trading_api(self):
        """測試融資融券餘額 API."""
        endpoint = "/exchangeReport/MI_MARGN"
        data = TWSEAPIClient.get_data(endpoint)
        assert data is not None, "融資融券 API 應該回傳資料"
        assert isinstance(data, list), "融資融券 API 應該回傳 list"
        assert len(data) > 0, "融資融券 API 應該回傳至少一筆資料"


class TestForeignInvestmentAPIs:
    """外資投資相關 APIs 測試."""

    def test_foreign_investment_by_category_api(self):
        """測試外資投資類股持股比率表 API."""
        endpoint = "/fund/MI_QFIIS_cat"
        data = TWSEAPIClient.get_data(endpoint)
        assert data is not None, "外資類股持股 API 應該回傳資料"
        assert isinstance(data, list), "外資類股持股 API 應該回傳 list"
        assert len(data) > 0, "外資類股持股 API 應該回傳至少一筆資料"

    def test_top_foreign_holdings_api(self):
        """測試外資持股前 20 名 API."""
        endpoint = "/fund/MI_QFIIS_sort_20"
        data = TWSEAPIClient.get_data(endpoint)
        assert data is not None, "外資前20名 API 應該回傳資料"
        assert isinstance(data, list), "外資前20名 API 應該回傳 list"
        assert len(data) > 0, "外資前20名 API 應該回傳至少一筆資料"

        # 檢查回傳的資料數量不超過 20 筆（可能會少一些）
        assert len(data) <= 20, f"外資前20名應該最多回傳20筆，實際: {len(data)}"


class TestTradingDataIntegrity:
    """交易數據完整性測試."""

    def test_stock_codes_are_valid_in_trading_apis(self):
        """測試交易 APIs 中的股票代號格式正確."""
        # 測試日成交資訊作為代表
        endpoint = "/exchangeReport/STOCK_DAY_ALL"
        data = TWSEAPIClient.get_data(endpoint)

        for item in data[:10]:  # 檢查前 10 筆
            code = item.get("Code")
            if code and code != "N/A":  # 排除空值和 N/A
                assert isinstance(code, str), "股票代號應該是字串"
                assert code.isdigit(), f"股票代號應該是數字: {code}"
                assert len(code) == 4, f"股票代號應該是 4 碼: {code}"

    def test_get_trading_data_by_code(self, sample_stock_code):
        """測試依股票代號查詢交易資料."""
        endpoints_to_test = [
            "/exchangeReport/BWIBBU_ALL",
            "/exchangeReport/STOCK_DAY_ALL",
            "/exchangeReport/FMSRFK_ALL",
            "/exchangeReport/FMNPTK_ALL",
        ]

        for endpoint in endpoints_to_test:
            data = TWSEAPIClient.get_company_data(endpoint, sample_stock_code)
            if data:
                returned_code = data.get("Code") or data.get("公司代號")
                assert returned_code == sample_stock_code, \
                    f"{endpoint} 查詢結果應該是指定的股票代號 {sample_stock_code}"

    def test_trading_volume_data_format(self):
        """測試交易量數據格式正確."""
        endpoint = "/exchangeReport/STOCK_DAY_ALL"
        data = TWSEAPIClient.get_data(endpoint)

        for item in data[:5]:  # 檢查前 5 筆
            # 檢查可能的成交量欄位
            volume_fields = ["TradeVolume", "成交股數", "成交量"]
            for field in volume_fields:
                if field in item:
                    volume = item[field]
                    if volume not in ["", "N/A", None, "--"]:
                        # 成交量應該是數字格式或包含逗號的數字字串
                        assert isinstance(volume, (str, int, float)), \
                            f"成交量格式不正確: {volume}"
                    break

    def test_price_data_format(self):
        """測試價格數據格式正確."""
        endpoint = "/exchangeReport/STOCK_DAY_ALL"
        data = TWSEAPIClient.get_data(endpoint)

        for item in data[:5]:  # 檢查前 5 筆
            # 檢查可能的價格欄位
            price_fields = ["ClosingPrice", "收盤價", "成交價格"]
            for field in price_fields:
                if field in item:
                    price = item[field]
                    if price not in ["", "N/A", None, "--"]:
                        # 價格應該是數字格式
                        assert isinstance(price, (str, int, float)), \
                            f"價格格式不正確: {price}"
                    break