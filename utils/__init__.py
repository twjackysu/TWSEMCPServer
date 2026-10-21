"""Utility modules for TWStockMCPServer."""

from .api_client import TWSEAPIClient
from .types import TWSEDataItem, DataFormatter
from .config import APIConfig, DisplayConfig, TestConfig
from .constants import (
    DEFAULT_DISPLAY_LIMIT,
    MSG_NO_DATA,
    MSG_QUERY_FAILED,
    MSG_NO_DATA_FOR_CODE,
    MSG_NO_MATCHING_DATA,
    MSG_OFFSET_OUT_OF_RANGE,
    MSG_TOTAL_RECORDS,
    SUMMARY_ROW_LABELS,
)
from .formatters import (
    format_properties_with_values_multiline,
    format_multiple_records,
    is_empty_or_na,
    has_meaningful_data,
    filter_meaningful_fields,
    format_meaningful_fields_only,
    format_list_response,
    create_simple_list_formatter,
    truncate,
    cap_rows,
    printed,
)
from .date_helper import roc_to_ad, ad_to_roc
from .errors import InvalidArgument
from .pagination import Page, Paged

__all__ = [
    "TWSEAPIClient",
    "TWSEDataItem",
    "DataFormatter",
    "APIConfig",
    "DisplayConfig",
    "TestConfig",
    "DEFAULT_DISPLAY_LIMIT",
    "MSG_NO_DATA",
    "MSG_QUERY_FAILED",
    "MSG_NO_DATA_FOR_CODE",
    "MSG_NO_MATCHING_DATA",
    "MSG_OFFSET_OUT_OF_RANGE",
    "MSG_TOTAL_RECORDS",
    "SUMMARY_ROW_LABELS",
    "format_properties_with_values_multiline",
    "format_multiple_records",
    "is_empty_or_na",
    "has_meaningful_data",
    "filter_meaningful_fields",
    "format_meaningful_fields_only",
    "format_list_response",
    "create_simple_list_formatter",
    "truncate",
    "cap_rows",
    "printed",
    "roc_to_ad",
    "ad_to_roc",
    "InvalidArgument",
    "Page",
    "Paged",
]