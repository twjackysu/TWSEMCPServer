"""E2E tests for trading-related APIs."""

import pytest
from utils.api_client import TWSEAPIClient


class TestStockTradingAPIs:
    """股票交易相關 APIs 測試."""

    def test_stock_valuation_ratios_schema(self):
        """測試個股本益比等評價指標 schema."""
        endpoint = "/exchangeReport/BWIBBU_ALL"
        data = TWSEAPIClient.get_data(endpoint)
        
        first_item = data[0]

        # 檢查所有必要欄位
        expected_fields = [
            "Date",           # 日期 (民國年 YYYMMDD)
            "Code",           # 股票代號
            "Name",           # 股票名稱
            "PEratio",        # 本益比
            "DividendYield",  # 殖利率
            "PBratio",        # 股價淨值比
        ]
        
        for field in expected_fields:
            assert field in first_item, f"欄位 '{field}' 應該存在於本益比資料中"
        
        # 驗證 Date 格式 (應該是 7 位數字，民國年 YYYMMDD，如 1141029)
        date_value = first_item.get("Date")
        if date_value:
            assert isinstance(date_value, str), "Date 應該是字串"
            assert date_value.isdigit(), f"Date 應該是數字字串，但得到 '{date_value}'"
            assert len(date_value) == 7, f"Date 應該是 7 位數（民國年 YYYMMDD），但得到 '{date_value}'"

    def test_daily_trading_schema(self):
        """測試個股日成交資訊 schema."""
        endpoint = "/exchangeReport/STOCK_DAY_ALL"
        data = TWSEAPIClient.get_data(endpoint)
        
        first_item = data[0]

        # 檢查所有必要欄位
        expected_fields = [
            "Date",          # 日期 (民國年 YYYMMDD)
            "Code",          # 股票代號
            "Name",          # 股票名稱
            "TradeVolume",   # 成交股數
            "TradeValue",    # 成交金額
            "OpeningPrice",  # 開盤價
            "HighestPrice",  # 最高價
            "LowestPrice",   # 最低價
            "ClosingPrice",  # 收盤價
            "Change",        # 漲跌
            "Transaction",   # 成交筆數
        ]
        
        for field in expected_fields:
            assert field in first_item, f"欄位 '{field}' 應該存在於日成交資訊中"
        
        # 驗證 Date 格式 (應該是 7 位數字，民國年 YYYMMDD，如 1141029)
        date_value = first_item.get("Date")
        if date_value:
            assert isinstance(date_value, str), "Date 應該是字串"
            assert date_value.isdigit(), f"Date 應該是數字字串，但得到 '{date_value}'"
            assert len(date_value) == 7, f"Date 應該是 7 位數（民國年 YYYMMDD），但得到 '{date_value}'"

    def test_monthly_trading_schema(self):
        """測試個股月成交資訊 schema."""
        endpoint = "/exchangeReport/FMSRFK_ALL"
        data = TWSEAPIClient.get_data(endpoint)
        
        first_item = data[0]

        # 檢查所有必要欄位
        expected_fields = [
            "Month",              # 月份 (民國年月 YYMM)
            "Code",               # 股票代號
            "Name",               # 股票名稱
            "HighestPrice",       # 最高價
            "LowestPrice",        # 最低價
            "WeightedAvgPriceAB", # 加權平均價
            "Transaction",        # 成交筆數
            "TradeValueA",        # 成交金額
            "TradeVolumeB",       # 成交股數
            "TurnoverRatio",      # 週轉率
        ]
        
        for field in expected_fields:
            assert field in first_item, f"欄位 '{field}' 應該存在於月成交資訊中"
        
        # 驗證 Month 格式 (應該是 5 位數字，民國年月 YYMM，如 11409)
        month_value = first_item.get("Month")
        if month_value:
            assert isinstance(month_value, str), "Month 應該是字串"
            assert month_value.isdigit(), f"Month 應該是數字字串，但得到 '{month_value}'"
            assert len(month_value) == 5, f"Month 應該是 5 位數（民國年月 YYMM），但得到 '{month_value}'"

    def test_yearly_trading_schema(self):
        """測試個股年成交資訊 schema."""
        endpoint = "/exchangeReport/FMNPTK_ALL"
        data = TWSEAPIClient.get_data(endpoint)
        
        first_item = data[0]

        # 檢查所有必要欄位
        expected_fields = [
            "Year",            # 年度 (民國年 YYY)
            "Code",            # 股票代號
            "Name",            # 股票名稱
            "TradeVolume",     # 成交股數
            "TradeValue",      # 成交金額
            "Transaction",     # 成交筆數
            "HighestPrice",    # 最高價
            "HDate",           # 最高價日期
            "LowestPrice",     # 最低價
            "LDate",           # 最低價日期
            "AvgClosingPrice", # 平均收盤價
        ]
        
        for field in expected_fields:
            assert field in first_item, f"欄位 '{field}' 應該存在於年成交資訊中"
        
        # 驗證 Year 格式 (應該是 3 位數字，民國年 YYY，如 113)
        year_value = first_item.get("Year")
        if year_value:
            assert isinstance(year_value, str), "Year 應該是字串"
            assert year_value.isdigit(), f"Year 應該是數字字串，但得到 '{year_value}'"
            assert len(year_value) == 3, f"Year 應該是 3 位數（民國年 YYY），但得到 '{year_value}'"

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

    def test_real_time_stats_schema(self):
        """測試 5 秒委託成交統計 API schema."""
        endpoint = "/exchangeReport/MI_5MINS"
        data = TWSEAPIClient.get_data(endpoint)
        
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


class TestForeignInvestmentAPIs:
    """外資投資相關 APIs 測試."""

    def test_foreign_top_20_api(self):
        """測試外資持有前20大股票 API schema."""
        endpoint = "/fund/MI_QFIIS_sort_20"
        data = TWSEAPIClient.get_data(endpoint)

        # 檢查回傳的資料數量不超過 20 筆（可能會少一些）
        if len(data) > 0:
            assert len(data) <= 20, f"前20名按成交量前20應該最多回傳20筆，實際: {len(data)}"


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


    def test_top_20_volume_stocks_schema(self):
        """測試集中市場每日成交量前二十名證券 (MI_INDEX20) schema."""
        endpoint = "/exchangeReport/MI_INDEX20"
        data = TWSEAPIClient.get_data(endpoint)
        
        if len(data) > 0:
            assert len(data) <= 20, f"成交量前二十名應該最多 20 筆，但得到 {len(data)} 筆"
        
        first_item = data[0]
        
        # 驗證必要欄位存在
        expected_fields = [
            "Date",          # 交易日期
            "Rank",          # 排名
            "Code",          # 股票代號
            "Name",          # 股票名稱
            "TradeVolume",   # 成交量
            "Transaction",   # 成交筆數
            "OpeningPrice",  # 開盤價
            "HighestPrice",  # 最高價
            "LowestPrice",   # 最低價
            "ClosingPrice",  # 收盤價
            "Dir",           # 漲跌方向
            "Change",        # 漲跌價差
            "LastBestBidPrice",  # 最後最佳買價
            "LastBestAskPrice",  # 最後最佳賣價
        ]
        
        for field in expected_fields:
            assert field in first_item, f"欄位 '{field}' 應該存在於成交量前二十名證券資料中"
        
        # 驗證 Date 格式（西元年格式，如 20251029）
        date_value = first_item.get("Date")
        if date_value:
            assert isinstance(date_value, str), "Date 應該是字串"
            assert date_value.isdigit(), f"Date 應該是數字字串，但得到 '{date_value}'"
            assert len(date_value) == 8, f"Date 應該是 8 位數（YYYYMMDD），但得到 '{date_value}'"
        
        # 驗證 Rank 是數字字串
        rank_value = first_item.get("Rank")
        if rank_value:
            assert rank_value.isdigit(), f"Rank 應該是數字字串，但得到 '{rank_value}'"


class TestBlockTradingAPIs:
    """鉅額交易相關 APIs 測試."""

    @pytest.mark.parametrize("endpoint", [
        "/block/BFIAUU_d",
        "/block/BFIAUU_m",
        "/block/BFIAMU_H",
    ])
    def test_block_trading_apis_have_basic_fields(self, endpoint):
        """測試鉅額交易相關 APIs 都有基本欄位."""
        data = TWSEAPIClient.get_data(endpoint)
        # 只在有數據時進行測試
        if data and len(data) > 0:
            first_item = data[0]
            # 確保至少有基本欄位存在
            assert len(first_item) > 0, f"{endpoint} 應該至少包含一些欄位"


class TestAnnouncementAPIs:
    """公告相關 APIs 測試."""

    def test_market_gain_loss_statistics_schema(self):
        """測試集中市場漲跌證券數統計表 schema."""
        endpoint = "/opendata/twtazu_od"
        data = TWSEAPIClient.get_data(endpoint)
        
        first_item = data[0]
        
        # 驗證必要欄位存在
        expected_fields = [
            "出表日期",  # 報表日期
            "類型",      # 類型（整體市場/股票/等）
            "上漲",      # 上漲家數
            "漲停",      # 漲停家數
            "下跌",      # 下跌家數
            "跌停",      # 跌停家數
            "持平",      # 持平家數
            "未成交",    # 未成交家數
            "無比價",    # 無比價家數
        ]
        
        for field in expected_fields:
            assert field in first_item, f"欄位 '{field}' 應該存在於漲跌證券數統計資料中"
        
        # 驗證出表日期格式（民國年格式，如 1141029）
        date_value = first_item.get("出表日期")
        if date_value:
            assert isinstance(date_value, str), "出表日期應該是字串"
            assert date_value.isdigit(), f"出表日期應該是數字字串，但得到 '{date_value}'"
            assert len(date_value) == 7, f"出表日期應該是 7 位數（民國年 YYYMMDD），但得到 '{date_value}'"

    def test_abnormal_accumulated_notice_stocks_schema(self):
        """測試集中市場公布注意累計次數異常資訊 schema."""
        endpoint = "/announcement/notetrans"
        data = TWSEAPIClient.get_data(endpoint)
        
        first_item = data[0]
        
        # 驗證必要欄位存在
        expected_fields = [
            "Number",                                   # 編號
            "Code",                                     # 股票代號
            "Name",                                     # 股票名稱
            "RecentlyMetAttentionSecuritiesCriteria",  # 符合注意標準
        ]
        
        for field in expected_fields:
            assert field in first_item, f"欄位 '{field}' 應該存在於注意累計次數異常資訊中"
        
        # 注意：當沒有異常資料時，API 會回傳 Number="0" 且 Code 為空字串
        # 這是正常情況，不是錯誤

    def test_today_notice_stocks_schema(self):
        """測試集中市場當日公布注意股票 schema."""
        endpoint = "/announcement/notice"
        data = TWSEAPIClient.get_data(endpoint)
        
        first_item = data[0]
        
        # 驗證必要欄位存在
        expected_fields = [
            "Number",                    # 編號
            "Code",                      # 股票代號
            "Name",                      # 股票名稱
            "NumberOfAnnouncement",      # 公布次數
            "TradingInfoForAttention",   # 交易資訊注意事項
            "Date",                      # 日期
            "ClosingPrice",              # 收盤價
            "PE",                        # 本益比
        ]
        
        for field in expected_fields:
            assert field in first_item, f"欄位 '{field}' 應該存在於當日公布注意股票資料中"
        
        # 注意：當沒有注意股票時，API 會回傳 Number="0" 且 Code 為空字串
        # 這是正常情況，不是錯誤

    @pytest.mark.parametrize("endpoint", [
        "/holidaySchedule/holidaySchedule",
        "/opendata/t187ap19",
    ])
    def test_announcement_apis_have_basic_fields(self, endpoint):
        """測試公告相關 APIs 都有基本欄位."""
        data = TWSEAPIClient.get_data(endpoint)
        first_item = data[0]
        # 確保至少有基本欄位存在
        assert len(first_item) > 0, f"{endpoint} 應該至少包含一些欄位"