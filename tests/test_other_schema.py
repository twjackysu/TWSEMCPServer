"""Test other APIs schema to detect field name changes."""

import pytest
from utils import TWSEAPIClient
from .schema_definitions import API_SCHEMA_MAP


class TestOtherAPISchema:
    """Test that other APIs return expected field names."""

    def test_fund_basic_info_schema(self):
        """Test /opendata/t187ap47_L has required fields."""
        endpoint = "/opendata/t187ap47_L"
        data = TWSEAPIClient.get_data(endpoint)
        assert len(data) > 0, "API should return data"
        
        first_item = data[0]
        required_fields = API_SCHEMA_MAP[endpoint]
        
        for field in required_fields:
            assert field in first_item, f"Missing field: {field}. Available fields: {list(first_item.keys())}"

    def test_bond_redemption_schema(self):
        """Test /exchangeReport/BFI61U has required fields."""
        endpoint = "/exchangeReport/BFI61U"
        data = TWSEAPIClient.get_data(endpoint)
        assert len(data) > 0, "API should return data"
        
        first_item = data[0]
        required_fields = API_SCHEMA_MAP[endpoint]
        
        for field in required_fields:
            assert field in first_item, f"Missing field: {field}. Available fields: {list(first_item.keys())}"

    def test_holiday_schedule_schema(self):
        """Test /holidaySchedule/holidaySchedule has required fields."""
        endpoint = "/holidaySchedule/holidaySchedule"
        data = TWSEAPIClient.get_data(endpoint)
        assert len(data) > 0, "API should return data"
        
        first_item = data[0]
        required_fields = API_SCHEMA_MAP[endpoint]
        
        for field in required_fields:
            assert field in first_item, f"Missing field: {field}. Available fields: {list(first_item.keys())}"
