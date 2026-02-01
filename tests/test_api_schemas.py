"""Generic schema validation tests for all TWSE APIs.

This test suite automatically validates that all API endpoints
return the expected field names defined in schema_definitions.py.
"""

import pytest
from utils import TWSEAPIClient
from tests.schema_definitions import get_all_endpoints, get_required_fields


@pytest.mark.parametrize("endpoint", get_all_endpoints())
def test_api_schema(endpoint):
    """
    Test that API endpoint returns expected field names.
    
    This test will fail if:
    1. The API is unreachable
    2. The API returns no data
    3. The API field names have changed
    
    When this test fails, check:
    1. Is the TWSE API down?
    2. Did they change the field names? Update schema_definitions.py
    3. Did they change the response structure?
    """
    # Get data from API
    data = TWSEAPIClient.get_data(endpoint)
    
    # Verify API returned data
    assert len(data) > 0, f"API {endpoint} returned no data"
    
    # Get expected fields for this endpoint
    required_fields = get_required_fields(endpoint)
    
    # Check first item has all required fields
    first_item = data[0]
    actual_fields = set(first_item.keys())
    
    for field in required_fields:
        assert field in actual_fields, (
            f"API {endpoint} missing field: '{field}'\n"
            f"Expected fields: {required_fields}\n"
            f"Actual fields: {sorted(actual_fields)}\n"
            f"\nThis likely means TWSE changed their API schema. "
            f"Please update the code and schema_definitions.py"
        )


def test_all_endpoints_defined():
    """Verify that we have schema definitions for all used endpoints."""
    # This is a meta-test to ensure we don't forget to add schema definitions
    # You should update this list when you add new endpoints to your code
    endpoints = get_all_endpoints()
    
    # Verify we have at least these critical endpoints
    critical_endpoints = [
        "/opendata/t187ap18",  # broker basic info
        "/exchangeReport/STOCK_DAY_ALL",  # daily trading
    ]
    
    for endpoint in critical_endpoints:
        assert endpoint in endpoints, (
            f"Critical endpoint {endpoint} not in schema definitions. "
            f"Please add it to tests/schema_definitions.py"
        )
