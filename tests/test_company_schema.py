"""Test company API schemas to detect field name changes."""

import pytest
from utils import TWSEAPIClient
from .schema_definitions import API_SCHEMA_MAP


class TestCompanyAPISchema:
    """Test that company APIs return expected field names."""

    def test_board_insufficient_shares_schema(self):
        """Test /opendata/t187ap08_L has required fields."""
        endpoint = "/opendata/t187ap08_L"
        data = TWSEAPIClient.get_data(endpoint)
        assert len(data) > 0, "API should return data"
        
        first_item = data[0]
        required_fields = API_SCHEMA_MAP[endpoint]
        
        for field in required_fields:
            assert field in first_item, f"Missing field: {field}. Available fields: {list(first_item.keys())}"

    def test_independent_directors_schema(self):
        """Test /opendata/t187ap30_L has required fields."""
        endpoint = "/opendata/t187ap30_L"

        data = TWSEAPIClient.get_data(endpoint)
        assert len(data) > 0, "API should return data"
        
        first_item = data[0]
        required_fields = API_SCHEMA_MAP[endpoint]
        
        for field in required_fields:
            assert field in first_item, f"Missing field: {field}. Available fields: {list(first_item.keys())}"

    def test_disposal_stocks_schema(self):
        """Test /announcement/punish has required fields."""
        endpoint = "/announcement/punish"

        data = TWSEAPIClient.get_data(endpoint)
        assert len(data) > 0, "API should return data"
        
        first_item = data[0]
        required_fields = API_SCHEMA_MAP[endpoint]
        
        for field in required_fields:
            assert field in first_item, f"Missing field: {field}. Available fields: {list(first_item.keys())}"

    def test_board_insufficient_consecutive_schema(self):
        """Test /opendata/t187ap10_L has required fields."""
        endpoint = "/opendata/t187ap10_L"

        data = TWSEAPIClient.get_data(endpoint)
        assert len(data) > 0, "API should return data"
        
        first_item = data[0]
        required_fields = API_SCHEMA_MAP[endpoint]
        
        for field in required_fields:
            assert field in first_item, f"Missing field: {field}. Available fields: {list(first_item.keys())}"

    def test_ownership_changes_schema(self):
        """Test /opendata/t187ap24_L has required fields."""
        endpoint = "/opendata/t187ap24_L"

        data = TWSEAPIClient.get_data(endpoint)
        assert len(data) > 0, "API should return data"
        
        first_item = data[0]
        required_fields = API_SCHEMA_MAP[endpoint]
        
        for field in required_fields:
            assert field in first_item, f"Missing field: {field}. Available fields: {list(first_item.keys())}"

    def test_business_scope_changes_schema(self):
        """Test /opendata/t187ap25_L has required fields."""
        endpoint = "/opendata/t187ap25_L"

        data = TWSEAPIClient.get_data(endpoint)
        assert len(data) > 0, "API should return data"
        
        # Filter out empty records
        valid_data = [item for item in data if item.get("公司代號") and item.get("公司名稱")]
        if not valid_data:
            pytest.skip("No valid data with company code and name")
        
        first_item = valid_data[0]
        required_fields = API_SCHEMA_MAP[endpoint]
        
        for field in required_fields:
            assert field in first_item, f"Missing field: {field}. Available fields: {list(first_item.keys())}"

    def test_board_pledged_shares_schema(self):
        """Test /opendata/t187ap09_L has required fields."""
        endpoint = "/opendata/t187ap09_L"

        data = TWSEAPIClient.get_data(endpoint)
        assert len(data) > 0, "API should return data"
        
        first_item = data[0]
        required_fields = API_SCHEMA_MAP[endpoint]
        
        for field in required_fields:
            assert field in first_item, f"Missing field: {field}. Available fields: {list(first_item.keys())}"

    def test_cumulative_voting_schema(self):
        """Test /opendata/t187ap34_L has required fields."""
        endpoint = "/opendata/t187ap34_L"

        data = TWSEAPIClient.get_data(endpoint)
        assert len(data) > 0, "API should return data"
        
        first_item = data[0]
        required_fields = API_SCHEMA_MAP[endpoint]
        
        for field in required_fields:
            assert field in first_item, f"Missing field: {field}. Available fields: {list(first_item.keys())}"

    def test_shareholder_proposal_schema(self):
        """Test /opendata/t187ap35_L has required fields."""
        endpoint = "/opendata/t187ap35_L"

        data = TWSEAPIClient.get_data(endpoint)
        assert len(data) > 0, "API should return data"
        
        first_item = data[0]
        required_fields = API_SCHEMA_MAP[endpoint]
        
        for field in required_fields:
            assert field in first_item, f"Missing field: {field}. Available fields: {list(first_item.keys())}"

    def test_ceo_dual_role_schema(self):
        """Test /opendata/t187ap33_L has required fields."""
        endpoint = "/opendata/t187ap33_L"

        data = TWSEAPIClient.get_data(endpoint)
        assert len(data) > 0, "API should return data"
        
        first_item = data[0]
        required_fields = API_SCHEMA_MAP[endpoint]
        
        for field in required_fields:
            assert field in first_item, f"Missing field: {field}. Available fields: {list(first_item.keys())}"
