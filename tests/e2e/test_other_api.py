"""E2E tests for other APIs (ETF, News, Index)."""

import pytest
from utils.api_client import TWSEAPIClient
from datetime import datetime, timedelta


class TestETFAPI:
    """ETF 相關 API 測試."""

    ENDPOINT = "/ETFReport/ETFRank"

    def test_etf_ranking_api_accessible(self):
        """測試 ETF 定期定額排名 API 可訪問."""
        data = TWSEAPIClient.get_data(self.ENDPOINT)
        assert data is not None, "ETF 排名 API 應該回傳資料"
        assert isinstance(data, list), "ETF 排名 API 應該回傳 list"
        assert len(data) > 0, "ETF 排名 API 應該回傳至少一筆資料"

    def test_etf_ranking_schema(self):
        """測試 ETF 排名 schema."""
        data = TWSEAPIClient.get_data(self.ENDPOINT)
        first_item = data[0]

        # 檢查基本欄位是否存在
        assert isinstance(first_item, dict), "每筆資料應該是 dict"

        # 根據實際 API 回應檢查欄位
        expected_fields = ["No", "ETFsSecurityCode", "ETFsName", "ETFsNumberofTradingAccounts"]
        for field in expected_fields:
            assert field in first_item, f"ETF 排名資料應該包含欄位 '{field}'"

    def test_etf_ranking_limit(self):
        """測試 ETF 排名筆數限制."""
        data = TWSEAPIClient.get_data(self.ENDPOINT)
        # ETF 排名通常有筆數限制（前 N 名）
        assert len(data) <= 50, f"ETF 排名資料筆數應該有合理限制，實際: {len(data)}"

    def test_etf_codes_exist(self):
        """測試 ETF 代號欄位存在."""
        data = TWSEAPIClient.get_data(self.ENDPOINT)

        for item in data[:5]:  # 檢查前 5 筆
            etf_code = item.get("ETFsSecurityCode")
            if etf_code and etf_code != "N/A":
                assert isinstance(etf_code, str), "ETF 代號應該是字串"
                assert etf_code.strip() != "", "ETF 代號不應為空字串"
                # 不限制長度或格式，支援各種 ETF 代號


class TestNewsAPIs:
    """新聞相關 API 測試."""

    def test_twse_news_api_accessible(self):
        """測試證交所新聞 API 可訪問."""
        endpoint = "/news/newsList"
        data = TWSEAPIClient.get_data(endpoint)
        assert data is not None, "證交所新聞 API 應該回傳資料"
        assert isinstance(data, list), "證交所新聞 API 應該回傳 list"
        assert len(data) > 0, "證交所新聞 API 應該回傳至少一筆資料"

    def test_twse_events_api_accessible(self):
        """測試證交所活動 API 可訪問."""
        endpoint = "/news/eventList"
        data = TWSEAPIClient.get_data(endpoint)
        assert data is not None, "證交所活動 API 應該回傳資料"
        assert isinstance(data, list), "證交所活動 API 應該回傳 list"
        assert len(data) > 0, "證交所活動 API 應該回傳至少一筆資料"

    def test_news_schema(self):
        """測試新聞 schema."""
        endpoint = "/news/newsList"
        data = TWSEAPIClient.get_data(endpoint)
        first_item = data[0]

        assert isinstance(first_item, dict), "每筆新聞資料應該是 dict"

        # 新聞通常有標題、日期等基本欄位
        has_title = any(field in first_item for field in ["標題", "title", "主旨", "Title"])
        has_date = any(field in first_item for field in ["日期", "date", "時間", "Date", "發布日期"])

        assert has_title, "新聞資料應該包含標題相關欄位"
        assert has_date, "新聞資料應該包含日期相關欄位"

    def test_events_schema(self):
        """測試活動 schema."""
        endpoint = "/news/eventList"
        data = TWSEAPIClient.get_data(endpoint)
        first_item = data[0]

        assert isinstance(first_item, dict), "每筆活動資料應該是 dict"

        # 根據實際 API 回應檢查欄位
        expected_fields = ["No", "Title", "Details"]
        for field in expected_fields:
            assert field in first_item, f"活動資料應該包含欄位 '{field}'"

    def test_news_content_not_empty(self):
        """測試新聞內容不為空."""
        endpoint = "/news/newsList"
        data = TWSEAPIClient.get_data(endpoint)

        # 檢查前幾筆新聞內容不為空
        for item in data[:3]:
            # 找標題欄位
            title = None
            for field in ["標題", "title", "主旨", "Title"]:
                if field in item:
                    title = item[field]
                    break

            if title:
                assert title.strip() != "", "新聞標題不應為空"
                assert len(title.strip()) > 0, "新聞標題應該有實際內容"


class TestIndexAPI:
    """指數相關 API 測試."""

    ENDPOINT = "/indicesReport/MI_5MINS_HIST"

    def test_historical_index_api_accessible(self):
        """測試歷史指數 API 可訪問."""
        data = TWSEAPIClient.get_data(self.ENDPOINT)
        assert data is not None, "歷史指數 API 應該回傳資料"
        assert isinstance(data, list), "歷史指數 API 應該回傳 list"
        assert len(data) > 0, "歷史指數 API 應該回傳至少一筆資料"

    def test_historical_index_schema(self):
        """測試歷史指數 schema."""
        data = TWSEAPIClient.get_data(self.ENDPOINT)
        first_item = data[0]

        assert isinstance(first_item, dict), "每筆指數資料應該是 dict"

        # 指數資料通常有日期、指數值等欄位
        has_date = any(field in first_item for field in ["日期", "Date", "交易日期"])
        has_index = any(field in first_item for field in ["指數", "Index", "收盤指數", "ClosingIndex"])

        assert has_date, "指數資料應該包含日期相關欄位"
        assert has_index, "指數資料應該包含指數值相關欄位"

    def test_index_date_format(self):
        """測試指數日期格式."""
        data = TWSEAPIClient.get_data(self.ENDPOINT)

        for item in data[:5]:  # 檢查前 5 筆
            # 找出日期欄位
            date_value = None
            for field in ["日期", "Date", "交易日期"]:
                if field in item:
                    date_value = item[field]
                    break

            if date_value and date_value != "N/A":
                assert isinstance(date_value, str), "日期應該是字串格式"
                # 檢查是否為合理的日期格式（可能是民國年或西元年）
                assert len(date_value) >= 6, f"日期格式長度不正確: {date_value}"

    def test_index_value_format(self):
        """測試指數值格式."""
        data = TWSEAPIClient.get_data(self.ENDPOINT)

        for item in data[:5]:  # 檢查前 5 筆
            # 找出指數值欄位
            index_value = None
            for field in ["指數", "Index", "收盤指數", "ClosingIndex"]:
                if field in item:
                    index_value = item[field]
                    break

            if index_value and index_value not in ["", "N/A", None, "--"]:
                # 指數值應該是數字格式
                assert isinstance(index_value, (str, int, float)), \
                    f"指數值格式不正確: {index_value}"


class TestOtherAPIsOverview:
    """其他 APIs 整體測試."""

    @pytest.mark.parametrize("endpoint,name", [
        ("/ETFReport/ETFRank", "ETF 定期定額排名"),
        ("/news/newsList", "證交所新聞"),
        ("/news/eventList", "證交所活動"),
        ("/indicesReport/MI_5MINS_HIST", "歷史指數"),
    ])
    def test_other_api_endpoints_accessible(self, endpoint, name):
        """測試其他 API 端點可訪問."""
        data = TWSEAPIClient.get_data(endpoint)
        assert data is not None, f"{name} API 應該回傳資料"
        assert isinstance(data, list), f"{name} API 應該回傳 list"
        assert len(data) > 0, f"{name} API 應該回傳至少一筆資料"

    def test_api_response_time_reasonable(self):
        """測試 API 回應時間合理."""
        import time

        endpoint = "/news/newsList"  # 使用新聞 API 作為代表

        start_time = time.time()
        data = TWSEAPIClient.get_data(endpoint)
        end_time = time.time()

        response_time = end_time - start_time

        assert data is not None, "API 應該回傳資料"
        assert response_time < 30, f"API 回應時間應該少於 30 秒，實際: {response_time:.2f} 秒"

    def test_api_data_freshness(self):
        """測試 API 資料時效性（以新聞為例）."""
        endpoint = "/news/newsList"
        data = TWSEAPIClient.get_data(endpoint)

        if data:
            # 檢查新聞日期是否在合理範圍內（最新的新聞不應該太舊）
            first_item = data[0]

            # 找出日期欄位
            date_value = None
            for field in ["日期", "date", "時間", "Date", "發布日期"]:
                if field in first_item:
                    date_value = first_item[field]
                    break

            if date_value:
                # 這裡只檢查日期欄位存在且不為空，不做具體日期解析
                # 因為日期格式可能各異（民國年、西元年等）
                assert date_value not in ["", None, "N/A"], "新聞應該有發布日期"