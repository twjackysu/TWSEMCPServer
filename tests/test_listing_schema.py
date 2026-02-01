"""Tests for company listing API schemas.

These tests verify that the TWSE listing APIs return the expected field names.
"""

import pytest
from utils.api_client import TWSEAPIClient
from .schema_definitions import API_SCHEMA_MAP


class TestListingAPISchema:
    """Test suite for company listing API field validation."""

    def test_applylistingForeign_schema(self):
        """Test /company/applylistingForeign API schema."""
        endpoint = "/company/applylistingForeign"

        data = TWSEAPIClient.get_data(endpoint)
        assert isinstance(data, list), "Expected list response"
        assert len(data) > 0, "Expected non-empty list"

        required_fields = API_SCHEMA_MAP[endpoint]
        
        first_item = data[0]
        assert isinstance(first_item, dict), "Expected dict items"
        actual_fields = list(first_item.keys())
        
        missing_fields = [f for f in required_fields if f not in actual_fields]
        assert not missing_fields, f"Missing fields: {missing_fields}. Expected: {required_fields}, Actual: {actual_fields}"

    def test_newlisting_schema(self):
        """Test /company/newlisting API schema."""
        endpoint = "/company/newlisting"

        data = TWSEAPIClient.get_data(endpoint)
        assert isinstance(data, list), "Expected list response"
        assert len(data) > 0, "Expected non-empty list"

        required_fields = API_SCHEMA_MAP[endpoint]
        
        first_item = data[0]
        assert isinstance(first_item, dict), "Expected dict items"
        actual_fields = list(first_item.keys())
        
        missing_fields = [f for f in required_fields if f not in actual_fields]
        assert not missing_fields, f"Missing fields: {missing_fields}. Expected: {required_fields}, Actual: {actual_fields}"

    def test_suspendListingCsvAndHtml_schema(self):
        """Test /company/suspendListingCsvAndHtml API schema."""
        endpoint = "/company/suspendListingCsvAndHtml"

        data = TWSEAPIClient.get_data(endpoint)
        assert isinstance(data, list), "Expected list response"
        assert len(data) > 0, "Expected non-empty list"

        required_fields = API_SCHEMA_MAP[endpoint]
        
        first_item = data[0]
        assert isinstance(first_item, dict), "Expected dict items"
        actual_fields = list(first_item.keys())
        
        missing_fields = [f for f in required_fields if f not in actual_fields]
        assert not missing_fields, f"Missing fields: {missing_fields}. Expected: {required_fields}, Actual: {actual_fields}"

    def test_applylistingLocal_schema(self):
        """Test /company/applylistingLocal API schema."""
        endpoint = "/company/applylistingLocal"

        data = TWSEAPIClient.get_data(endpoint)
        assert isinstance(data, list), "Expected list response"
        assert len(data) > 0, "Expected non-empty list"

        required_fields = API_SCHEMA_MAP[endpoint]
        
        first_item = data[0]
        assert isinstance(first_item, dict), "Expected dict items"
        actual_fields = list(first_item.keys())
        
        missing_fields = [f for f in required_fields if f not in actual_fields]
        assert not missing_fields, f"Missing fields: {missing_fields}. Expected: {required_fields}, Actual: {actual_fields}"
