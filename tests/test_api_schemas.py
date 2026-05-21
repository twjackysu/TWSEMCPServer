"""Tool field dependency tests.

Verifies that fields our tools explicitly access (via .get("field")) are still
present in live API responses.  Extra fields added by TWSE are ignored — only
missing required fields cause a failure, because that means a tool will silently
return "N/A" instead of real data.

To add a new endpoint: edit tests/tool_field_dependencies.py.
"""

import pytest
from utils import TWSEAPIClient
from tests.tool_field_dependencies import TOOL_REQUIRED_FIELDS


@pytest.mark.parametrize("endpoint", sorted(TOOL_REQUIRED_FIELDS.keys()))
def test_tool_required_fields_present(endpoint):
    """All fields our tools hardcode must still exist in the live API response."""
    data = TWSEAPIClient.get_data(endpoint)

    if not data:
        pytest.skip(f"API {endpoint} returned no data; cannot verify field presence")

    first_item = data[0]
    assert isinstance(first_item, dict), (
        f"API {endpoint} should return a list of dicts, got {type(first_item).__name__}"
    )

    required = TOOL_REQUIRED_FIELDS[endpoint]
    actual = set(first_item.keys())
    missing = [f for f in required if f not in actual]

    assert not missing, (
        f"API {endpoint} removed fields that our tools use.\n"
        f"Missing: {missing}\n"
        f"Actual fields now: {sorted(actual)}\n"
        f"Fix: update the tool's .get() calls to use the new field names, "
        f"then update tool_field_dependencies.py to match."
    )
