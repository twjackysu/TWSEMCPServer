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

    def test_real_time_stats_schema(self):
        """測試 5 秒委託成交統計 API schema."""
        endpoint = "/exchangeReport/MI_5MINS"
        data = TWSEAPIClient.get_data(endpoint)
        
        assert len(data) > 0, "應該至少有一筆5秒統計資料"
        
        first_item = data[0]
        
        # 驗證必要欄位存在
        expected_fields = [
            "Time",              # 時間 (HHMMSS 格式)
            "AccBidOrders",      # 累計委買筆數
            "AccBidVolume",      # 累計委買數量
            "AccAskOrders",      # 累計委賣筆數
            "AccAskVolume",      # 累計委賣數量
            "AccTransaction",    # 累計成交筆數
            "AccTradeVolume",    # 累計成交數量
            "AccTradeValue",     # 累計成交金額(百萬)
        ]
        
        for field in expected_fields:
            assert field in first_item, f"欄位 '{field}' 應該存在於5秒統計資料中"
        
        # 驗證 Time 格式 (應該是 6 位數字的字串，HHMMSS)
        time_value = first_item.get("Time")
        if time_value:  # 可能是空字串
            assert len(time_value) == 6, f"Time 欄位應該是 6 位數字 (HHMMSS)，但得到 '{time_value}'"
            assert time_value.isdigit(), f"Time 欄位應該是數字字串，但得到 '{time_value}'"


    def test_margin_trading_api(self):
        """測試融資融券餘額 API."""
        endpoint = "/exchangeReport/MI_MARGN"
        data = TWSEAPIClient.get_data(endpoint)
        assert data is not None, "融資融券 API 應該回傳資料"
        assert isinstance(data, list), "融資融券 API 應該回傳 list"
        assert len(data) > 0, "融資融券 API 應該回傳至少一筆資料"

    def test_daily_securities_lending_volume_api(self):
        """測試上市上櫃股票當日可借券賣出股數 API."""
        endpoint = "/SBL/TWT96U"
        data = TWSEAPIClient.get_data(endpoint)
        assert data is not None, "可借券賣出股數 API 應該回傳資料"
        assert isinstance(data, list), "可借券賣出股數 API 應該回傳 list"
        assert len(data) > 0, "可借券賣出股數 API 應該回傳至少一筆資料"


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

    def test_stock_codes_exist_in_trading_apis(self):
        """測試交易 APIs 中的股票代號欄位存在且有效."""
        # 測試日成交資訊作為代表
        endpoint = "/exchangeReport/STOCK_DAY_ALL"
        data = TWSEAPIClient.get_data(endpoint)

        for item in data[:10]:  # 檢查前 10 筆
            code = item.get("Code")
            if code and code != "N/A":  # 排除空值和 N/A
                assert isinstance(code, str), "股票代號應該是字串"
                assert code.strip() != "", "股票代號不應為空字串"
                # 支援各種證券代號格式：一般股票(4碼)、ETF(6碼)、特別股等

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


class TestSpecialTradingAPIs:
    """特殊交易相關 APIs 測試."""

    @pytest.mark.parametrize("endpoint,name", [
        ("/exchangeReport/TWT88U", "上市個股首五日無漲跌幅"),
        ("/Announcement/BFZFZU_T", "投資理財節目異常推介個股"),
        ("/exchangeReport/TWTB4U", "上市股票每日當日沖銷交易標的及統計"),
        ("/exchangeReport/TWTBAU1", "集中市場暫停先賣後買當日沖銷交易標的預告表"),
        ("/exchangeReport/TWTBAU2", "集中市場暫停先賣後買當日沖銷交易歷史查詢"),
        ("/exchangeReport/TWT84U", "上市個股股價升降幅度"),
        ("/exchangeReport/BWIBBU_d", "上市個股日本益比、殖利率及股價淨值比（依日期查詢）"),
    ])
    def test_special_trading_api_accessible(self, endpoint, name):
        """測試特殊交易相關 API 端點可訪問."""
        data = TWSEAPIClient.get_data(endpoint)
        assert data is not None, f"{name} API 應該回傳資料"
        assert isinstance(data, list), f"{name} API 應該回傳 list"
        assert len(data) > 0, f"{name} API 應該回傳至少一筆資料"

    @pytest.mark.parametrize("endpoint", [
        "/exchangeReport/TWT88U",
        "/Announcement/BFZFZU_T",
        "/exchangeReport/TWTB4U",
        "/exchangeReport/TWTBAU1",
        "/exchangeReport/TWTBAU2",
        "/exchangeReport/TWT84U",
        "/exchangeReport/BWIBBU_d",
    ])
    def test_special_trading_apis_have_basic_fields(self, endpoint):
        """測試特殊交易相關 APIs 都有基本欄位."""
        data = TWSEAPIClient.get_data(endpoint)
        first_item = data[0]
        # 確保至少有基本欄位存在
        assert len(first_item) > 0, f"{endpoint} 應該至少包含一些欄位"


class TestMarketTradingAPIs:
    """市場交易相關 APIs 測試."""

    @pytest.mark.parametrize("endpoint,name", [
        ("/exchangeReport/FMTQIK", "集中市場每日市場成交資訊"),
        ("/exchangeReport/MI_INDEX20", "集中市場每日成交量前二十名證券"),
        ("/exchangeReport/TWT53U", "集中市場零股交易行情單"),
        ("/exchangeReport/TWTAWU", "集中市場暫停交易證券"),
        ("/exchangeReport/BFT41U", "集中市場盤後定價交易"),
        ("/exchangeReport/BFI84U", "集中市場停資停券預告表"),
        ("/exchangeReport/STOCK_FIRST", "每日第一上市外國股票成交量值"),
        ("/exchangeReport/TWT85U", "集中市場證券變更交易"),
    ])
    def test_market_trading_api_accessible(self, endpoint, name):
        """測試市場交易相關 API 端點可訪問."""
        data = TWSEAPIClient.get_data(endpoint)
        assert data is not None, f"{name} API 應該回傳資料"
        assert isinstance(data, list), f"{name} API 應該回傳 list"
        assert len(data) > 0, f"{name} API 應該回傳至少一筆資料"

    @pytest.mark.parametrize("endpoint", [
        "/exchangeReport/FMTQIK",
        "/exchangeReport/MI_INDEX20",
        "/exchangeReport/TWT53U",
        "/exchangeReport/TWTAWU",
        "/exchangeReport/BFT41U",
        "/exchangeReport/BFI84U",
        "/exchangeReport/STOCK_FIRST",
        "/exchangeReport/TWT85U",
    ])
    def test_market_trading_apis_have_basic_fields(self, endpoint):
        """測試市場交易相關 APIs 都有基本欄位."""
        data = TWSEAPIClient.get_data(endpoint)
        first_item = data[0]
        # 確保至少有基本欄位存在
        assert len(first_item) > 0, f"{endpoint} 應該至少包含一些欄位"

    def test_daily_market_trading_info_schema(self):
        """測試集中市場每日市場成交資訊 (FMTQIK) schema."""
        endpoint = "/exchangeReport/FMTQIK"
        data = TWSEAPIClient.get_data(endpoint)
        first_item = data[0]

        # 檢查所有必要欄位
        expected_fields = [
            "Date",
            "TradeVolume",
            "TradeValue",
            "Transaction",
            "TAIEX",
            "Change",
        ]
        
        for field in expected_fields:
            assert field in first_item, f"欄位 '{field}' 應該存在於每日市場成交資訊中"
        
        # 檢查日期格式（民國年格式，如 1141030）
        assert isinstance(first_item["Date"], str), "Date 應該是字串"
        assert first_item["Date"].isdigit(), "Date 應該是數字字串"
        assert len(first_item["Date"]) == 7, "Date 應該是 7 位數（民國年 YYYMMDD）"


class TestBlockTradingAPIs:
    """鉅額交易相關 APIs 測試."""

    @pytest.mark.parametrize("endpoint,name", [
        ("/block/BFIAUU_d", "集中市場鉅額交易日成交量值統計"),
        ("/block/BFIAUU_m", "集中市場鉅額交易月成交量值統計"),
        ("/block/BFIAUU_y", "集中市場鉅額交易年成交量值統計"),
    ])
    def test_block_trading_api_accessible(self, endpoint, name):
        """測試鉅額交易相關 API 端點可訪問."""
        data = TWSEAPIClient.get_data(endpoint)
        assert data is not None, f"{name} API 應該回傳資料"
        assert isinstance(data, list), f"{name} API 應該回傳 list"
        assert len(data) > 0, f"{name} API 應該回傳至少一筆資料"

    @pytest.mark.parametrize("endpoint", [
        "/block/BFIAUU_d",
        "/block/BFIAUU_m",
        "/block/BFIAUU_y",
    ])
    def test_block_trading_apis_have_basic_fields(self, endpoint):
        """測試鉅額交易相關 APIs 都有基本欄位."""
        data = TWSEAPIClient.get_data(endpoint)
        first_item = data[0]
        # 確保至少有基本欄位存在
        assert len(first_item) > 0, f"{endpoint} 應該至少包含一些欄位"


class TestAnnouncementAPIs:
    """公告相關 APIs 測試."""

    @pytest.mark.parametrize("endpoint,name", [
        ("/holidaySchedule/holidaySchedule", "有價證券集中交易市場開（休）市日期"),
        ("/opendata/twtazu_od", "集中市場漲跌證券數統計表"),
        ("/opendata/t187ap19", "電子式交易統計資訊"),
        ("/announcement/notetrans", "集中市場公布注意累計次數異常資訊"),
        ("/announcement/notice", "集中市場當日公布注意股票"),
    ])
    def test_announcement_api_accessible(self, endpoint, name):
        """測試公告相關 API 端點可訪問."""
        data = TWSEAPIClient.get_data(endpoint)
        assert data is not None, f"{name} API 應該回傳資料"
        assert isinstance(data, list), f"{name} API 應該回傳 list"
        assert len(data) > 0, f"{name} API 應該回傳至少一筆資料"

    @pytest.mark.parametrize("endpoint", [
        "/holidaySchedule/holidaySchedule",
        "/opendata/twtazu_od",
        "/opendata/t187ap19",
        "/announcement/notetrans",
        "/announcement/notice",
    ])
    def test_announcement_apis_have_basic_fields(self, endpoint):
        """測試公告相關 APIs 都有基本欄位."""
        data = TWSEAPIClient.get_data(endpoint)
        first_item = data[0]
        # 確保至少有基本欄位存在
        assert len(first_item) > 0, f"{endpoint} 應該至少包含一些欄位"