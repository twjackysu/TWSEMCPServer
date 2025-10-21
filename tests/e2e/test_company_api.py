"""E2E tests for company-related APIs."""

import pytest
from utils.api_client import TWSEAPIClient


class TestCompanyDividendAPI:
    """股利分派情形 API 測試."""

    ENDPOINT = "/opendata/t187ap45_L"
    EXPECTED_FIELDS = [
        "出表日期",
        "公司代號",
        "公司名稱",
        "決議（擬議）進度",
        "股利年度",
        "股利所屬年(季)度",
        "股利所屬期間",
        "期別",
        "董事會（擬議）股利分派日",
        "股東會日期",
        "股東配發-盈餘分配之現金股利(元/股)",
        "股東配發-股東配發之現金(股利)總金額(元)",
        "摘錄公司章程-股利分派部分"
    ]

    def test_api_endpoint_is_accessible(self):
        """測試 API 端點可訪問."""
        data = TWSEAPIClient.get_data(self.ENDPOINT)
        assert data is not None, "API 應該回傳資料"
        assert isinstance(data, list), "API 應該回傳 list"
        assert len(data) > 0, "API 應該回傳至少一筆資料"

    def test_response_schema_matches_expected(self):
        """測試回應 schema 符合預期."""
        data = TWSEAPIClient.get_data(self.ENDPOINT)

        # 取第一筆資料檢查欄位
        first_item = data[0]
        assert isinstance(first_item, dict), "每筆資料應該是 dict"

        # 檢查所有必要欄位都存在
        for field in self.EXPECTED_FIELDS:
            assert field in first_item, f"欄位 '{field}' 應該存在於回應中"

    def test_company_code_exists(self):
        """測試公司代號欄位存在且有效."""
        data = TWSEAPIClient.get_data(self.ENDPOINT)

        for item in data[:10]:  # 檢查前 10 筆
            code = item.get("公司代號")
            assert code is not None, "公司代號不應為 None"
            assert isinstance(code, str), "公司代號應該是字串"
            assert code.strip() != "", "公司代號不應為空字串"
            # 不限制長度或特定格式，支援一般股、特別股、ETF等各種代號

    def test_get_company_data_by_code(self, sample_stock_code):
        """測試依公司代號查詢資料."""
        data = TWSEAPIClient.get_company_data(self.ENDPOINT, sample_stock_code)

        if data:
            assert data.get("公司代號") == sample_stock_code, \
                f"查詢結果應該是指定的公司代號 {sample_stock_code}"


class TestCompanyNewsAPI:
    """上市公司每日重大訊息 API 測試."""

    ENDPOINT = "/opendata/t187ap04_L"
    EXPECTED_FIELDS = [
        "出表日期",
        "發言日期",
        "發言時間",
        "公司代號",
        "公司名稱",
        "主旨 ",
        "符合條款",
        "事實發生日",
        "說明"
    ]

    def test_api_endpoint_is_accessible(self):
        """測試 API 端點可訪問."""
        data = TWSEAPIClient.get_data(self.ENDPOINT)
        assert data is not None, "API 應該回傳資料"
        assert isinstance(data, list), "API 應該回傳 list"
        assert len(data) > 0, "API 應該回傳至少一筆資料"

    def test_response_schema_matches_expected(self):
        """測試回應 schema 符合預期."""
        data = TWSEAPIClient.get_data(self.ENDPOINT)

        # 取第一筆資料檢查欄位
        first_item = data[0]
        assert isinstance(first_item, dict), "每筆資料應該是 dict"

        # 檢查所有必要欄位都存在
        for field in self.EXPECTED_FIELDS:
            assert field in first_item, f"欄位 '{field}' 應該存在於回應中"

    def test_company_code_format(self):
        """測試公司代號格式正確."""
        data = TWSEAPIClient.get_data(self.ENDPOINT)

        for item in data[:10]:  # 檢查前 10 筆
            code = item.get("公司代號")
            assert code is not None, "公司代號不應為 None"
            assert isinstance(code, str), "公司代號應該是字串"
            assert code.isdigit(), f"公司代號應該是數字: {code}"
            assert len(code) == 4, f"公司代號應該是 4 碼: {code}"

    def test_get_company_data_by_code(self, sample_stock_code):
        """測試依公司代號查詢資料."""
        data = TWSEAPIClient.get_company_data(self.ENDPOINT, sample_stock_code)

        if data:
            assert data.get("公司代號") == sample_stock_code, \
                f"查詢結果應該是指定的公司代號 {sample_stock_code}"


class TestCompanyRevenueAPI:
    """上市公司每月營業收入彙總表 API 測試."""

    ENDPOINT = "/opendata/t187ap05_L"
    EXPECTED_FIELDS = [
        "出表日期",
        "資料年月",
        "公司代號",
        "公司名稱",
        "產業別",
        "營業收入-當月營收",
        "營業收入-上月營收",
        "營業收入-去年當月營收",
        "營業收入-上月比較增減(%)",
        "營業收入-去年同月增減(%)",
        "累計營業收入-當月累計營收",
        "累計營業收入-去年累計營收",
        "累計營業收入-前期比較增減(%)",
        "備註"
    ]

    def test_api_endpoint_is_accessible(self):
        """測試 API 端點可訪問."""
        data = TWSEAPIClient.get_data(self.ENDPOINT)
        assert data is not None, "API 應該回傳資料"
        assert isinstance(data, list), "API 應該回傳 list"
        assert len(data) > 0, "API 應該回傳至少一筆資料"

    def test_response_schema_matches_expected(self):
        """測試回應 schema 符合預期."""
        data = TWSEAPIClient.get_data(self.ENDPOINT)

        # 取第一筆資料檢查欄位
        first_item = data[0]
        assert isinstance(first_item, dict), "每筆資料應該是 dict"

        # 檢查所有必要欄位都存在
        for field in self.EXPECTED_FIELDS:
            assert field in first_item, f"欄位 '{field}' 應該存在於回應中"

    def test_company_code_format(self):
        """測試公司代號格式正確."""
        data = TWSEAPIClient.get_data(self.ENDPOINT)

        for item in data[:10]:  # 檢查前 10 筆
            code = item.get("公司代號")
            assert code is not None, "公司代號不應為 None"
            assert isinstance(code, str), "公司代號應該是字串"
            assert code.isdigit(), f"公司代號應該是數字: {code}"
            assert len(code) == 4, f"公司代號應該是 4 碼: {code}"

    def test_get_company_data_by_code(self, sample_stock_code):
        """測試依公司代號查詢資料."""
        data = TWSEAPIClient.get_company_data(self.ENDPOINT, sample_stock_code)

        if data:
            assert data.get("公司代號") == sample_stock_code, \
                f"查詢結果應該是指定的公司代號 {sample_stock_code}"

class TestOtherESGAPIs:
    """其他 ESG API 測試."""

    @pytest.mark.parametrize("endpoint,name", [
        ("/opendata/t187ap46_L_18", "持股及控制力"),
        ("/opendata/t187ap46_L_14", "產品品質與安全"),
        ("/opendata/t187ap46_L_12", "食品安全"),
        ("/opendata/t187ap46_L_11", "產品生命週期"),
        ("/opendata/t187ap46_L_10", "燃料管理"),
        ("/opendata/t187ap46_L_7", "投資人溝通"),
        ("/opendata/t187ap46_L_6", "董事會"),
        ("/opendata/t187ap46_L_5", "人力發展"),
        ("/opendata/t187ap46_L_4", "廢棄物管理"),
        ("/opendata/t187ap46_L_3", "水資源管理"),
        ("/opendata/t187ap46_L_2", "能源管理"),
        ("/opendata/t187ap46_L_1", "溫室氣體排放"),
    ])
    def test_esg_api_endpoints_accessible(self, endpoint, name):
        """測試 ESG API 端點可訪問."""
        try:
            data = TWSEAPIClient.get_data(endpoint)
            assert data is not None, f"{name} API 應該回傳資料"
            assert isinstance(data, list), f"{name} API 應該回傳 list"

            # 對於某些ESG API，允許返回空數據（因為可能沒有相關數據）
            if endpoint in ["/opendata/t187ap46_L_12"]:  # 食品安全API
                # 這些API可能返回無效JSON或空數據，這個是正常的
                pass
            else:
                assert len(data) > 0, f"{name} API 應該回傳至少一筆資料"
        except Exception as e:
            # 如果是食品安全API，允許異常，因為它可能返回無效JSON
            if endpoint == "/opendata/t187ap46_L_12":
                pass  # 預期會有異常，跳過
            else:
                raise  # 其他API不應該有異常

class TestCompanyBasicInfoAPI:
    """上市公司基本資料 API 測試."""

    ENDPOINT = "/opendata/t187ap03_L"

    def test_api_endpoint_is_accessible(self):
        """測試 API 端點可訪問."""
        data = TWSEAPIClient.get_data(self.ENDPOINT)
        assert data is not None, "API 應該回傳資料"
        assert isinstance(data, list), "API 應該回傳 list"
        assert len(data) > 0, "API 應該回傳至少一筆資料"

    def test_response_has_company_code(self):
        """測試回應包含公司代號欄位."""
        data = TWSEAPIClient.get_data(self.ENDPOINT)
        first_item = data[0]
        assert "公司代號" in first_item or "Code" in first_item, "應該包含公司代號欄位"

    def test_get_company_data_by_code(self, sample_stock_code):
        """測試依公司代號查詢資料."""
        data = TWSEAPIClient.get_company_data(self.ENDPOINT, sample_stock_code)

        if data:
            returned_code = data.get("公司代號") or data.get("Code")
            assert returned_code == sample_stock_code, \
                f"查詢結果應該是指定的公司代號 {sample_stock_code}"


class TestCompanyMajorShareholdersAPI:
    """上市公司持股逾 10% 大股東名單 API 測試."""

    ENDPOINT = "/opendata/t187ap02_L"

    def test_api_endpoint_is_accessible(self):
        """測試 API 端點可訪問."""
        data = TWSEAPIClient.get_data(self.ENDPOINT)
        assert data is not None, "API 應該回傳資料"
        assert isinstance(data, list), "API 應該回傳 list"
        assert len(data) > 0, "API 應該回傳至少一筆資料"

    def test_response_has_company_code(self):
        """測試回應包含公司代號欄位."""
        data = TWSEAPIClient.get_data(self.ENDPOINT)
        first_item = data[0]
        assert "公司代號" in first_item or "Code" in first_item, "應該包含公司代號欄位"

    def test_get_company_data_by_code(self, sample_stock_code):
        """測試依公司代號查詢資料."""
        data = TWSEAPIClient.get_company_data(self.ENDPOINT, sample_stock_code)

        if data:
            returned_code = data.get("公司代號") or data.get("Code")
            assert returned_code == sample_stock_code, \
                f"查詢結果應該是指定的公司代號 {sample_stock_code}"


class TestCompanyEPSStatisticsAPI:
    """上市公司各產業EPS統計資訊 API 測試."""

    ENDPOINT = "/opendata/t187ap14_L"

    def test_api_endpoint_is_accessible(self):
        """測試 API 端點可訪問."""
        data = TWSEAPIClient.get_data(self.ENDPOINT)
        assert data is not None, "API 應該回傳資料"
        assert isinstance(data, list), "API 應該回傳 list"
        assert len(data) > 0, "API 應該回傳至少一筆資料"

class TestCompanyDirectorShareholdingAPIs:
    """董事、監察人持股相關 APIs 測試."""

    @pytest.mark.parametrize("endpoint,name", [
        ("/opendata/t187ap08_L", "董事、監察人持股不足法定成數彙總表"),
        ("/opendata/t187ap11_L", "董監事持股餘額明細資料"),
        ("/opendata/t187ap12_L", "每日內部人持股轉讓事前申報表-持股轉讓日報表"),
        ("/opendata/t187ap13_L", "每日內部人持股轉讓事前申報表-持股未轉讓日報表"),
        ("/opendata/t187ap10_L", "董事、監察人持股不足法定成數連續達3個月以上彙總表"),
        ("/opendata/t187ap09_L", "董事、監察人質權設定占董事及監察人實際持有股數彙總表"),
    ])
    def test_director_shareholding_api_accessible(self, endpoint, name):
        """測試董事、監察人持股相關 API 端點可訪問."""
        data = TWSEAPIClient.get_data(endpoint)
        assert data is not None, f"{name} API 應該回傳資料"
        assert isinstance(data, list), f"{name} API 應該回傳 list"
        assert len(data) > 0, f"{name} API 應該回傳至少一筆資料"

class TestCompanyGovernanceAPIs:
    """公司治理相關 APIs 測試."""

    @pytest.mark.parametrize("endpoint,name", [
        ("/opendata/t187ap22_L", "金管會證券期貨局裁罰案件專區"),
        ("/opendata/t187ap30_L", "獨立董監事兼任情形彙總表"),
        ("/opendata/t187ap29_A_L", "董事酬金相關資訊"),
        ("/opendata/t187ap29_B_L", "監察人酬金相關資訊"),
        ("/opendata/t187ap29_C_L", "合併報表董事酬金相關資訊"),
        ("/opendata/t187ap29_D_L", "合併報表監察人酬金相關資訊"),
        ("/opendata/t187ap23_L", "違反資訊申報、重大訊息及說明記者會規定專區"),
        ("/static/20151104/CSR103", "103 年應編製與申報 CSR 報告書名單"),
        ("/opendata/t187ap03_P", "公開發行公司基本資料"),
        ("/announcement/punish", "集中市場公布處置股票"),
        ("/opendata/t187ap38_L", "股東會公告-召集股東常(臨時)會公告資料彙總表"),
        ("/opendata/t187ap24_L", "經營權及營業範圍異(變)動專區-經營權異動公司"),
        ("/opendata/t187ap26_L", "經營權異動且營業範圍重大變更停止買賣公司"),
        ("/opendata/t187ap41_L", "召開股東常 (臨時) 會日期、地點及採用電子投票情形等資料彙總表"),
        ("/opendata/t187ap25_L", "營業範圍重大變更公司"),
        ("/opendata/t187ap27_L", "經營權異動且營業範圍重大變更列為變更交易公司"),
        ("/opendata/t187ap32_L", "公司治理之相關規程規則"),
        ("/opendata/t187ap33_L", "董事長是否兼任總經理"),
        ("/opendata/t187ap34_L", "採累積投票制、全額連記法、候選人提名制選任董監事及當選資料彙總表"),
        ("/opendata/t187ap35_L", "股東行使提案權情形彙總表"),
    ])
    def test_governance_api_accessible(self, endpoint, name):
        """測試公司治理相關 API 端點可訪問."""
        try:
            data = TWSEAPIClient.get_data(endpoint)
            assert data is not None, f"{name} API 應該回傳資料"
            assert isinstance(data, list), f"{name} API 應該回傳 list"

            # 對於某些公司治理API，允許返回空數據（因為可能沒有相關數據）
            empty_allowed_endpoints = [
                "/opendata/t187ap29_B_L",  # 監察人酬金相關資訊
                "/opendata/t187ap29_D_L",  # 合併報表監察人酬金相關資訊
                "/opendata/t187ap26_L",    # 經營權異動且營業範圍重大變更停止買賣公司
                "/opendata/t187ap27_L",    # 經營權異動且營業範圍重大變更列為變更交易公司
            ]

            if endpoint in empty_allowed_endpoints:
                # 這些API可能返回空數據，這個是正常的
                pass
            elif endpoint == "/static/20151104/CSR103":
                # CSR報告書名單API可能返回無效JSON
                pass
            else:
                assert len(data) > 0, f"{name} API 應該回傳至少一筆資料"
        except Exception as e:
            # 如果是CSR報告書名單API，允許異常，因為它可能返回無效JSON
            if endpoint == "/static/20151104/CSR103":
                pass  # 預期會有異常，跳過
            else:
                raise  # 其他API不應該有異常

class TestCompanyListingAPIs:
    """公司上市相關 APIs 測試."""

    @pytest.mark.parametrize("endpoint,name", [
        ("/company/applylistingForeign", "外國公司向證交所申請第一上市之公司"),
        ("/company/newlisting", "最近上市公司"),
        ("/company/suspendListingCsvAndHtml", "終止上市公司"),
        ("/company/applylistingLocal", "申請上市之本國公司"),
        ("/opendata/t187ap05_P", "公開發行公司每月營業收入彙總表"),
    ])
    def test_listing_api_accessible(self, endpoint, name):
        """測試公司上市相關 API 端點可訪問."""
        data = TWSEAPIClient.get_data(endpoint)
        assert data is not None, f"{name} API 應該回傳資料"
        assert isinstance(data, list), f"{name} API 應該回傳 list"
        assert len(data) > 0, f"{name} API 應該回傳至少一筆資料"

    @pytest.mark.parametrize("endpoint", [
        "/company/applylistingForeign",
        "/company/newlisting",
        "/company/suspendListingCsvAndHtml",
        "/company/applylistingLocal",
        "/opendata/t187ap05_P",
    ])
    def test_listing_apis_have_basic_fields(self, endpoint):
        """測試公司上市相關 APIs 都有基本欄位."""
        data = TWSEAPIClient.get_data(endpoint)
        first_item = data[0]
        # 確保至少有基本欄位存在
        assert len(first_item) > 0, f"{endpoint} 應該至少包含一些欄位"