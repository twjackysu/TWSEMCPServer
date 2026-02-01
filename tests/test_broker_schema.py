"""Test broker API schema to detect field name changes."""

import pytest
from utils import TWSEAPIClient
from .schema_definitions import API_SCHEMA_MAP


class TestBrokerAPISchema:
    """Test that broker APIs return expected field names."""

    def test_broker_service_personnel_schema(self):
        """Test /opendata/t187ap01 has required fields."""
        endpoint = "/opendata/t187ap01"
        data = TWSEAPIClient.get_data(endpoint)
        assert len(data) > 0, "API should return data"
        
        first_item = data[0]
        required_fields = API_SCHEMA_MAP[endpoint]
        
        for field in required_fields:
            assert field in first_item, f"Missing field: {field}. Available fields: {list(first_item.keys())}"

    def test_broker_monthly_statements_schema(self):
        """Test /opendata/t187ap20 has required fields."""
        endpoint = "/opendata/t187ap20"
        data = TWSEAPIClient.get_data(endpoint)
        assert len(data) > 0, "API should return data"
        
        first_item = data[0]
        required_fields = API_SCHEMA_MAP[endpoint]
        
        for field in required_fields:
            assert field in first_item, f"Missing field: {field}. Available fields: {list(first_item.keys())}"

    def test_broker_income_expenditure_schema(self):
        """Test /opendata/t187ap21 has required fields."""
        endpoint = "/opendata/t187ap21"
        data = TWSEAPIClient.get_data(endpoint)
        assert len(data) > 0, "API should return data"
        
        first_item = data[0]
        required_fields = API_SCHEMA_MAP[endpoint]
        
        for field in required_fields:
            assert field in first_item, f"Missing field: {field}. Available fields: {list(first_item.keys())}"

    def test_broker_basic_info_schema(self):
        """Test /opendata/t187ap18 has required fields."""
        endpoint = "/opendata/t187ap18"
        data = TWSEAPIClient.get_data(endpoint)
        assert len(data) > 0, "API should return data"
        
        first_item = data[0]
        required_fields = API_SCHEMA_MAP[endpoint]
        
        for field in required_fields:
            assert field in first_item, f"Missing field: {field}. Available fields: {list(first_item.keys())}"

    def test_broker_electronic_trading_schema(self):
        """Test /opendata/t187ap19 has required fields."""
        endpoint = "/opendata/t187ap19"
        data = TWSEAPIClient.get_data(endpoint)
        assert len(data) > 0, "API should return data"
        
        first_item = data[0]
        required_fields = API_SCHEMA_MAP[endpoint]
        
        for field in required_fields:
            assert field in first_item, f"Missing field: {field}. Available fields: {list(first_item.keys())}"

    def test_broker_gender_statistics_schema(self):
        """Test /opendata/OpenData_BRK01 has required fields."""
        endpoint = "/opendata/OpenData_BRK01"
        data = TWSEAPIClient.get_data(endpoint)
        assert len(data) > 0, "API should return data"
        
        first_item = data[0]
        required_fields = API_SCHEMA_MAP[endpoint]
        
        for field in required_fields:
            assert field in first_item, f"Missing field: {field}. Available fields: {list(first_item.keys())}"

    def test_broker_branch_info_schema(self):
        """Test /opendata/OpenData_BRK02 has required fields."""
        endpoint = "/opendata/OpenData_BRK02"
        data = TWSEAPIClient.get_data(endpoint)
        assert len(data) > 0, "API should return data"
        
        first_item = data[0]
        required_fields = API_SCHEMA_MAP[endpoint]
        
        for field in required_fields:
            assert field in first_item, f"Missing field: {field}. Available fields: {list(first_item.keys())}"

    def test_brokers_regular_investment_schema(self):
        """Test /brokerService/secRegData has required fields."""
        endpoint = "/brokerService/secRegData"
        data = TWSEAPIClient.get_data(endpoint)
        assert len(data) > 0, "API should return data"
        
        first_item = data[0]
        required_fields = API_SCHEMA_MAP[endpoint]
        
        for field in required_fields:
            assert field in first_item, f"Missing field: {field}. Available fields: {list(first_item.keys())}"

    def test_broker_headquarters_schema(self):
        """Test /brokerService/brokerList has required fields."""
        endpoint = "/brokerService/brokerList"
        data = TWSEAPIClient.get_data(endpoint)
        assert len(data) > 0, "API should return data"
        
        first_item = data[0]
        required_fields = API_SCHEMA_MAP[endpoint]
        
        for field in required_fields:
            assert field in first_item, f"Missing field: {field}. Available fields: {list(first_item.keys())}"
