"""Test other APIs schema to detect field name changes."""

import pytest
from utils import TWSEAPIClient


class TestOtherAPISchema:
    """Test that other APIs return expected field names."""

    def test_fund_basic_info_schema(self):
        """Test /opendata/t187ap47_L has required fields."""
        data = TWSEAPIClient.get_data("/opendata/t187ap47_L")
        assert len(data) > 0, "API should return data"
        
        first_item = data[0]
        required_fields = ["基金名稱", "基金代號", "基金種類"]
        
        for field in required_fields:
            assert field in first_item, f"Missing field: {field}. Available fields: {list(first_item.keys())}"

    def test_bond_redemption_schema(self):
        """Test /exchangeReport/BFI61U has required fields."""
        data = TWSEAPIClient.get_data("/exchangeReport/BFI61U")
        assert len(data) > 0, "API should return data"
        
        first_item = data[0]
        required_fields = ["債券名稱", "債券代號", "補息日期"]
        
        for field in required_fields:
            assert field in first_item, f"Missing field: {field}. Available fields: {list(first_item.keys())}"

    def test_holiday_schedule_schema(self):
        """Test /holidaySchedule/holidaySchedule has required fields."""
        data = TWSEAPIClient.get_data("/holidaySchedule/holidaySchedule")
        assert len(data) > 0, "API should return data"
        
        first_item = data[0]
        required_fields = ["日期", "是否為假期", "說明"]
        
        for field in required_fields:
            assert field in first_item, f"Missing field: {field}. Available fields: {list(first_item.keys())}"
