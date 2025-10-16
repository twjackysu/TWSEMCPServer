"""E2E tests for ESG-related APIs."""

import pytest
from utils.api_client import TWSEAPIClient
from utils.formatters import has_meaningful_data

class TestAnticompetitiveLitigationAPI:
    """反競爭行為法律訴訟 API 測試."""
    
    ENDPOINT = "/opendata/t187ap46_L_20"
    EXPECTED_FIELDS = [
        "出表日期",
        "報告年度", 
        "公司代號",
        "公司名稱",
        "因與反競爭行為條例相關的法律訴訟而造成的金錢損失總額(仟元)"
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
    
    def test_loss_amount_format(self):
        """測試損失金額格式正確."""
        data = TWSEAPIClient.get_data(self.ENDPOINT)
        
        for item in data[:10]:
            loss = item.get("因與反競爭行為條例相關的法律訴訟而造成的金錢損失總額(仟元)")
            assert loss is not None, "損失金額欄位不應為 None"
            # 應該是數字字串或 "0.000" 或 "N/A"
            assert isinstance(loss, str) or isinstance(loss, (int, float)), \
                f"損失金額格式不正確: {loss}"
    
    def test_get_company_data_by_code(self, sample_stock_code):
        """測試依公司代號查詢資料."""
        data = TWSEAPIClient.get_company_data(self.ENDPOINT, sample_stock_code)
        
        if data:
            assert data.get("公司代號") == sample_stock_code, \
                f"查詢結果應該是指定的公司代號 {sample_stock_code}"
    
    def test_filter_non_zero_losses(self):
        """測試過濾非零損失的邏輯."""
        data = TWSEAPIClient.get_data(self.ENDPOINT)
        
        # 使用 has_meaningful_data helper 函數
        filtered_data = [
            item for item in data 
            if isinstance(item, dict) and 
            has_meaningful_data(item, "因與反競爭行為條例相關的法律訴訟而造成的金錢損失總額(仟元)")
        ]
        
        # 檢查過濾後的資料都不是零
        for item in filtered_data:
            loss = item.get("因與反競爭行為條例相關的法律訴訟而造成的金錢損失總額(仟元)")
            assert loss not in ["0.000", "0", "N/A", "", None], \
                f"過濾後不應包含零值或 N/A: {loss}"
    
    def test_known_company_with_loss(self, sample_stock_code_with_data):
        """測試已知有損失的公司（大成 1210）."""
        data = TWSEAPIClient.get_company_data(self.ENDPOINT, sample_stock_code_with_data)
        
        if data:
            loss = data.get("因與反競爭行為條例相關的法律訴訟而造成的金錢損失總額(仟元)")
            # 這個測試可能會因為實際資料變化而失敗，這正是我們想要的！
            # 如果失敗，代表證交所的資料已更新
            assert loss not in ["0.000", "0", "N/A", "", None], \
                f"大成(1210)應該有訴訟損失資料，但得到: {loss}"


class TestInclusiveFinanceAPI:
    """普惠金融 API 測試."""
    
    ENDPOINT = "/opendata/t187ap46_L_17"
    EXPECTED_FIELDS = [
        "出表日期",
        "報告年度",
        "公司代號",
        "公司名稱",
        "對促進小型企業及社區發展的貸放件數(件)",
        "對促進小型企業及社區發展的貸放餘額(仟元)",
        "對缺少銀行服務之弱勢族群提供金融教育之參與人數(人)"
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
    
    def test_filter_meaningful_data(self):
        """測試過濾有意義資料的邏輯（任一欄位非零即保留）."""
        data = TWSEAPIClient.get_data(self.ENDPOINT)
        
        # 使用 has_meaningful_data helper 函數
        filtered_data = [
            item for item in data 
            if isinstance(item, dict) and 
            has_meaningful_data(item, [
                "對促進小型企業及社區發展的貸放件數(件)",
                "對促進小型企業及社區發展的貸放餘額(仟元)",
                "對缺少銀行服務之弱勢族群提供金融教育之參與人數(人)"
            ])
        ]
        
        # 檢查過濾後的資料至少有一個欄位不是零或 N/A
        for item in filtered_data:
            loan_count = item.get("對促進小型企業及社區發展的貸放件數(件)")
            loan_amount = item.get("對促進小型企業及社區發展的貸放餘額(仟元)")
            education_count = item.get("對缺少銀行服務之弱勢族群提供金融教育之參與人數(人)")
            
            # 至少一個欄位應該有意義的數據
            has_data = (
                loan_count not in ["0", "N/A", "", None] or
                loan_amount not in ["0.000", "0", "N/A", "", None] or
                education_count not in ["0", "N/A", "", None]
            )
            
            assert has_data, \
                f"過濾後的資料應該至少有一個欄位有意義: 貸放件數={loan_count}, 貸放餘額={loan_amount}, 教育人數={education_count}"


class TestOtherESGAPIs:
    """其他 ESG API 測試."""
    
    @pytest.mark.parametrize("endpoint,name", [
        ("/opendata/t187ap46_L_9", "功能性委員會"),
        ("/opendata/t187ap46_L_8", "氣候相關議題管理"),
        ("/opendata/t187ap46_L_19", "風險管理政策"),
        ("/opendata/t187ap46_L_13", "供應鏈管理"),
        ("/opendata/t187ap46_L_16", "資訊安全"),
        ("/opendata/t187ap46_L_17", "普惠金融"),
        ("/opendata/t187ap46_L_20", "反競爭行為法律訴訟"),
    ])
    def test_esg_api_endpoints_accessible(self, endpoint, name):
        """測試所有 ESG API 端點可訪問."""
        data = TWSEAPIClient.get_data(endpoint)
        assert data is not None, f"{name} API 應該回傳資料"
        assert isinstance(data, list), f"{name} API 應該回傳 list"
        assert len(data) > 0, f"{name} API 應該回傳至少一筆資料"
    
    @pytest.mark.parametrize("endpoint", [
        "/opendata/t187ap46_L_9",
        "/opendata/t187ap46_L_8",
        "/opendata/t187ap46_L_19",
        "/opendata/t187ap46_L_13",
        "/opendata/t187ap46_L_16",
        "/opendata/t187ap46_L_17",
        "/opendata/t187ap46_L_20",
    ])
    def test_esg_apis_have_company_code_field(self, endpoint):
        """測試所有 ESG API 都有公司代號欄位."""
        data = TWSEAPIClient.get_data(endpoint)
        first_item = data[0]
        assert "公司代號" in first_item, f"{endpoint} 應該包含公司代號欄位"
