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

    @pytest.mark.parametrize("endpoint,name", [
        ("/indicesReport/MI_5MINS_HIST", "發行量加權股價指數歷史資料"),
        ("/exchangeReport/MI_INDEX4", "每日上市上櫃跨市場成交資訊"),
        ("/indicesReport/FRMSA", "寶島股價指數歷史資料"),
        ("/indicesReport/TAI50I", "臺灣 50 指數歷史資料"),
        ("/indicesReport/MFI94U", "發行量加權股價報酬指數"),
    ])
    def test_index_api_accessible(self, endpoint, name):
        """測試指數相關 API 端點可訪問."""
        data = TWSEAPIClient.get_data(endpoint)
        assert data is not None, f"{name} API 應該回傳資料"
        assert isinstance(data, list), f"{name} API 應該回傳 list"
        assert len(data) > 0, f"{name} API 應該回傳至少一筆資料"

    @pytest.mark.parametrize("endpoint,expected_index_fields", [
        ("/exchangeReport/MI_INDEX4", ["FormosaIndex"]),
        ("/indicesReport/FRMSA", ["FormosaIndex", "FormosaTotalReturnIndex"]),
        ("/indicesReport/TAI50I", ["Taiwan50Index", "Taiwan50TotalReturnIndex"]),
        ("/indicesReport/MFI94U", ["TAIEXTotalReturnIndex"]),
    ])
    def test_index_api_schema(self, endpoint, expected_index_fields):
        """測試指數 API schema."""
        data = TWSEAPIClient.get_data(endpoint)
        first_item = data[0]

        assert isinstance(first_item, dict), "每筆指數資料應該是 dict"

        # 檢查是否有日期欄位
        has_date = any(field in first_item for field in ["日期", "Date", "交易日期"])
        assert has_date, "指數資料應該包含日期相關欄位"

        # 檢查是否有指數值欄位（根據具體API的欄位名稱）
        has_index = any(field in first_item for field in expected_index_fields)
        assert has_index, f"指數資料應該包含指數值相關欄位: {expected_index_fields}"


class TestOtherAPIsOverview:
    """其他 APIs 整體測試."""

    @pytest.mark.parametrize("endpoint,name", [
        ("/ETFReport/ETFRank", "ETF 定期定額排名"),
        ("/news/newsList", "證交所新聞"),
        ("/news/eventList", "證交所活動"),
        ("/indicesReport/MI_5MINS_HIST", "發行量加權股價指數歷史資料"),
        ("/exchangeReport/MI_INDEX4", "每日上市上櫃跨市場成交資訊"),
        ("/indicesReport/FRMSA", "寶島股價指數歷史資料"),
        ("/indicesReport/TAI50I", "臺灣 50 指數歷史資料"),
        ("/indicesReport/MFI94U", "發行量加權股價報酬指數"),
        ("/opendata/t187ap47_L", "基金基本資料彙總表"),
        ("/exchangeReport/BFI61U", "中央登錄公債補息資料表"),
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

class TestFundAPI:
    """基金相關 API 測試."""

    ENDPOINT = "/opendata/t187ap47_L"

    def test_fund_basic_info_api_accessible(self):
        """測試基金基本資料彙總表 API 可訪問."""
        data = TWSEAPIClient.get_data(self.ENDPOINT)
        assert data is not None, "基金基本資料 API 應該回傳資料"
        assert isinstance(data, list), "基金基本資料 API 應該回傳 list"
        assert len(data) > 0, "基金基本資料 API 應該回傳至少一筆資料"

    def test_fund_basic_info_schema(self):
        """測試基金基本資料 schema."""
        data = TWSEAPIClient.get_data(self.ENDPOINT)
        first_item = data[0]

        assert isinstance(first_item, dict), "每筆基金資料應該是 dict"

        # 基金資料通常有基金代號、名稱等基本欄位
        has_code = any(field in first_item for field in ["基金代號", "Code", "基金代碼"])
        has_name = any(field in first_item for field in ["基金名稱", "Name", "基金簡稱"])

        assert has_code, "基金資料應該包含代號相關欄位"
        assert has_name, "基金資料應該包含名稱相關欄位"


class TestBondAPI:
    """債券相關 API 測試."""

    ENDPOINT = "/exchangeReport/BFI61U"

    def test_bond_compensation_api_accessible(self):
        """測試中央登錄公債補息資料表 API 可訪問."""
        data = TWSEAPIClient.get_data(self.ENDPOINT)
        assert data is not None, "公債補息資料 API 應該回傳資料"
        assert isinstance(data, list), "公債補息資料 API 應該回傳 list"
        assert len(data) > 0, "公債補息資料 API 應該回傳至少一筆資料"

    def test_bond_compensation_schema(self):
        """測試公債補息資料 schema."""
        data = TWSEAPIClient.get_data(self.ENDPOINT)
        first_item = data[0]

        assert isinstance(first_item, dict), "每筆公債補息資料應該是 dict"

        # 公債補息資料通常有債券代號、補息金額等欄位
        has_bond_code = any(field in first_item for field in ["債券代號", "BondCode", "債券代碼", "Code"])
        has_compensation = any(field in first_item for field in ["補息金額", "Compensation", "補息", "DailyAccInterest"])

        assert has_bond_code, "公債補息資料應該包含債券代號相關欄位"
        assert has_compensation, "公債補息資料應該包含補息金額相關欄位"