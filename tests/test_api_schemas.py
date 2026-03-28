"""Generic live schema drift tests for monitored TWSE APIs."""

import pytest
from utils import TWSEAPIClient
from tests.schema_definitions import get_all_endpoints, get_required_fields


@pytest.mark.parametrize("endpoint", get_all_endpoints())
def test_api_schema(endpoint):
    """Compare the latest live response fields against the stored schema snapshot."""
    data = TWSEAPIClient.get_data(endpoint)

    if not data:
        pytest.skip(f"API {endpoint} currently returned no data; schema drift cannot be evaluated")

    required_fields = get_required_fields(endpoint)
    first_item = data[0]
    assert isinstance(first_item, dict), f"API {endpoint} should return dict items, got {type(first_item).__name__}"

    actual_fields = list(first_item.keys())
    missing_fields = [field for field in required_fields if field not in actual_fields]
    extra_fields = [field for field in actual_fields if field not in required_fields]

    assert set(actual_fields) == set(required_fields), (
        f"API {endpoint} schema changed.\n"
        f"Expected fields: {required_fields}\n"
        f"Actual fields: {actual_fields}\n"
        f"Missing fields: {missing_fields}\n"
        f"Extra fields: {extra_fields}\n"
        f"\nThis indicates the live API response no longer matches the published swagger schema."
    )


def test_all_endpoints_defined():
    """Verify that the consolidated snapshot suite still covers critical endpoints."""
    endpoints = get_all_endpoints()

    critical_endpoints = [
        "/opendata/t187ap18",  # broker basic info
        "/exchangeReport/STOCK_DAY_ALL",  # daily trading
        "/opendata/t187ap03_L",  # company basic info
        "/opendata/t187ap47_L",  # fund basic info
    ]

    for endpoint in critical_endpoints:
        assert endpoint in endpoints, (
            f"Critical endpoint {endpoint} not found in swagger-derived schema definitions. "
            f"Please verify https://openapi.twse.com.tw/v1/swagger.json"
        )
