"""Test broker API schema to detect field name changes."""

import pytest
from utils import TWSEAPIClient


class TestBrokerAPISchema:
    """Test that broker APIs return expected field names."""

    def test_broker_service_personnel_schema(self):
        """Test /opendata/t187ap01 has required fields."""
        data = TWSEAPIClient.get_data("/opendata/t187ap01")
        assert len(data) > 0, "API should return data"
        
        # Check first item has expected fields
        first_item = data[0]
        required_fields = ["職位", "出表日期", "合計", "受託買賣", "自行買賣"]
        
        for field in required_fields:
            assert field in first_item, f"Missing field: {field}. Available fields: {list(first_item.keys())}"

    def test_broker_monthly_statements_schema(self):
        """Test /opendata/t187ap20 has required fields."""
        data = TWSEAPIClient.get_data("/opendata/t187ap20")
        assert len(data) > 0, "API should return data"
        
        first_item = data[0]
        required_fields = ["出表日期", "券商代號", "券商名稱", "科目", "會計科目名稱", "本月借方總額", "本月貸方總額", "借方餘額"]
        
        for field in required_fields:
            assert field in first_item, f"Missing field: {field}. Available fields: {list(first_item.keys())}"

    def test_broker_income_expenditure_schema(self):
        """Test /opendata/t187ap21 has required fields."""
        data = TWSEAPIClient.get_data("/opendata/t187ap21")
        assert len(data) > 0, "API should return data"
        
        first_item = data[0]
        required_fields = ["出表日期", "券商代號", "券商名稱", "科目", "會計科目名稱", "本月金額", "累進金額"]
        
        for field in required_fields:
            assert field in first_item, f"Missing field: {field}. Available fields: {list(first_item.keys())}"

    def test_broker_basic_info_schema(self):
        """Test /opendata/t187ap18 has required fields."""
        data = TWSEAPIClient.get_data("/opendata/t187ap18")
        assert len(data) > 0, "API should return data"
        
        first_item = data[0]
        required_fields = ["券商(證券IB)簡稱", "證券代號", "設立日期"]
        
        for field in required_fields:
            assert field in first_item, f"Missing field: {field}. Available fields: {list(first_item.keys())}"

    def test_broker_electronic_trading_schema(self):
        """Test /opendata/t187ap19 has required fields."""
        data = TWSEAPIClient.get_data("/opendata/t187ap19")
        assert len(data) > 0, "API should return data"
        
        first_item = data[0]
        required_fields = ["出表日期", "成交月份", "成交筆數", "公司總成交筆數"]
        
        for field in required_fields:
            assert field in first_item, f"Missing field: {field}. Available fields: {list(first_item.keys())}"

    def test_broker_gender_statistics_schema(self):
        """Test /opendata/OpenData_BRK01 has required fields."""
        data = TWSEAPIClient.get_data("/opendata/OpenData_BRK01")
        assert len(data) > 0, "API should return data"
        
        first_item = data[0]
        required_fields = ["證券商代號", "男性員工人數", "女性員工人數", "總人數"]
        
        for field in required_fields:
            assert field in first_item, f"Missing field: {field}. Available fields: {list(first_item.keys())}"

    def test_broker_branch_info_schema(self):
        """Test /opendata/OpenData_BRK02 has required fields."""
        data = TWSEAPIClient.get_data("/opendata/OpenData_BRK02")
        assert len(data) > 0, "API should return data"
        
        first_item = data[0]
        required_fields = ["證券商代號", "證券商名稱", "地址", "電話"]
        
        for field in required_fields:
            assert field in first_item, f"Missing field: {field}. Available fields: {list(first_item.keys())}"

    def test_brokers_regular_investment_schema(self):
        """Test /brokerService/secRegData has required fields."""
        data = TWSEAPIClient.get_data("/brokerService/secRegData")
        assert len(data) > 0, "API should return data"
        
        first_item = data[0]
        required_fields = ["SecuritiesFirmCode", "Name", "BrokerageBusinessStartingDate", "WealthManagementBusinessStartingDate"]
        
        for field in required_fields:
            assert field in first_item, f"Missing field: {field}. Available fields: {list(first_item.keys())}"

    def test_broker_headquarters_schema(self):
        """Test /brokerService/brokerList has required fields."""
        data = TWSEAPIClient.get_data("/brokerService/brokerList")
        assert len(data) > 0, "API should return data"
        
        first_item = data[0]
        required_fields = ["Code", "Name", "EstablishmentDate", "Address", "Telephone"]
        
        for field in required_fields:
            assert field in first_item, f"Missing field: {field}. Available fields: {list(first_item.keys())}"
