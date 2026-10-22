"""Type definitions for TWSE API data structures."""

from typing import Any, Dict, Protocol

# One record of a TWSE OpenAPI list: the endpoint's published field names (Chinese or English,
# different for every endpoint) to their values, as the JSON gave them.
TWSEDataItem = Dict[str, Any]


class DataFormatter(Protocol):
    """Protocol for data formatting functions."""

    def __call__(self, item: TWSEDataItem, /) -> str:
        """Format a single data item into a string."""
        ...
