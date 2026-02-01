"""Tests for warrants trading API schemas.

These tests verify that the TWSE warrants APIs return the expected field names.
"""

import pytest
from utils.api_client import TWSEAPIClient
from .schema_definitions import API_SCHEMA_MAP


class TestWarrantsAPISchema:
    """Test suite for warrants API field validation."""

    def test_t187ap37_L_schema(self):
        """Test /opendata/t187ap37_L (Warrant Basic Info) API schema."""
        endpoint = "/opendata/t187ap37_L"

        data = TWSEAPIClient.get_data(endpoint)
        assert isinstance(data, list), "Expected list response"
        assert len(data) > 0, "Expected non-empty list"

        required_fields = API_SCHEMA_MAP[endpoint]
        
        first_item = data[0]
        assert isinstance(first_item, dict), "Expected dict items"
        actual_fields = list(first_item.keys())
        
        missing_fields = [f for f in required_fields if f not in actual_fields]
        assert not missing_fields, f"Missing fields: {missing_fields}. Expected: {required_fields}, Actual: {actual_fields}"

    def test_t187ap43_L_schema(self):
        """Test /opendata/t187ap43_L (Warrant Trader Count) API schema."""
        endpoint = "/opendata/t187ap43_L"

        data = TWSEAPIClient.get_data(endpoint)
        assert isinstance(data, list), "Expected list response"
        assert len(data) > 0, "Expected non-empty list"

        required_fields = API_SCHEMA_MAP[endpoint]
        
        first_item = data[0]
        assert isinstance(first_item, dict), "Expected dict items"
        actual_fields = list(first_item.keys())
        
        missing_fields = [f for f in required_fields if f not in actual_fields]
        assert not missing_fields, f"Missing fields: {missing_fields}. Expected: {required_fields}, Actual: {actual_fields}"

    def test_t187ap36_L_schema(self):
        """Test /opendata/t187ap36_L (Warrant Issuance Records) API schema."""
        endpoint = "/opendata/t187ap36_L"

        data = TWSEAPIClient.get_data(endpoint)
        assert isinstance(data, list), "Expected list response"
        assert len(data) > 0, "Expected non-empty list"

        required_fields = API_SCHEMA_MAP[endpoint]
        
        first_item = data[0]
        assert isinstance(first_item, dict), "Expected dict items"
        actual_fields = list(first_item.keys())
        
        missing_fields = [f for f in required_fields if f not in actual_fields]
        assert not missing_fields, f"Missing fields: {missing_fields}. Expected: {required_fields}, Actual: {actual_fields}"
