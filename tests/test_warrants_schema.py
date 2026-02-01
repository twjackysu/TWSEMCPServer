"""Tests for warrants trading API schemas.

These tests verify that the TWSE warrants APIs return the expected field names.
"""

import pytest
from utils.api_client import TWSEAPIClient


class TestWarrantsAPISchema:
    """Test suite for warrants API field validation."""

    def test_t187ap37_L_schema(self):
        """Test /opendata/t187ap37_L (Warrant Basic Info) API schema."""
        data = TWSEAPIClient.get_data("/opendata/t187ap37_L")
        assert isinstance(data, list), "Expected list response"
        assert len(data) > 0, "Expected non-empty list"

        required_fields = [
            "出表日期", "權證代號", "權證簡稱", "權證類型", "類別",
            "流動量提供者報價方式", "履約開始日", "最後交易日", "履約截止日",
            "發行單位數量(仟單位)", "結算方式(詳附註編號說明)", "標的證券/指數",
            "最新標的履約配發數量(每仟單位權證)", "原始履約價格(元)/履約指數",
            "原始上限價格(元)/上限指數", "原始下限價格(元)/下限指數",
            "最新履約價格(元)/履約指數", "最新上限價格(元)/上限指數",
            "最新下限價格(元)/下限指數", "備註"
        ]
        
        first_item = data[0]
        assert isinstance(first_item, dict), "Expected dict items"
        actual_fields = list(first_item.keys())
        
        missing_fields = [f for f in required_fields if f not in actual_fields]
        assert not missing_fields, f"Missing fields: {missing_fields}. Expected: {required_fields}, Actual: {actual_fields}"

    def test_t187ap43_L_schema(self):
        """Test /opendata/t187ap43_L (Warrant Trader Count) API schema."""
        data = TWSEAPIClient.get_data("/opendata/t187ap43_L")
        assert isinstance(data, list), "Expected list response"
        assert len(data) > 0, "Expected non-empty list"

        required_fields = ["出表日期", "日期", "人數"]
        
        first_item = data[0]
        assert isinstance(first_item, dict), "Expected dict items"
        actual_fields = list(first_item.keys())
        
        missing_fields = [f for f in required_fields if f not in actual_fields]
        assert not missing_fields, f"Missing fields: {missing_fields}. Expected: {required_fields}, Actual: {actual_fields}"

    def test_t187ap36_L_schema(self):
        """Test /opendata/t187ap36_L (Warrant Issuance Records) API schema."""
        data = TWSEAPIClient.get_data("/opendata/t187ap36_L")
        assert isinstance(data, list), "Expected list response"
        assert len(data) > 0, "Expected non-empty list"

        required_fields = [
            "出表日期", "發行人代號", "發行人名稱", "權證代號",
            "名稱", "標的代號", "標的名稱", "申請發行日期"
        ]
        
        first_item = data[0]
        assert isinstance(first_item, dict), "Expected dict items"
        actual_fields = list(first_item.keys())
        
        missing_fields = [f for f in required_fields if f not in actual_fields]
        assert not missing_fields, f"Missing fields: {missing_fields}. Expected: {required_fields}, Actual: {actual_fields}"
