"""Data formatting utilities."""

from typing import List, Union, Sequence
from .constants import MSG_TOTAL_RECORDS, MSG_MORE_RECORDS, DEFAULT_DISPLAY_LIMIT
from .types import TWSEDataItem, DataFormatter

def format_properties_with_values_multiline(data: TWSEDataItem) -> str:
    """
    Format dictionary properties as multiline string.
    
    Args:
        data: Dictionary with key-value pairs to format
        
    Returns:
        Formatted string with each property on a new line
    """
    if not data:
        return ""
    
    description_items = [f"{key}: {value}" for key, value in data.items()]
    return "\n".join(description_items)

def format_multiple_records(records: List[TWSEDataItem], separator: str = "-" * 30) -> str:
    """
    Format multiple records as a single string with separators.
    
    Args:
        records: List of dictionary records to format
        separator: String to separate records
        
    Returns:
        Formatted string with all records separated by separator
    """
    if not records:
        return ""
    
    formatted_items = []
    for record in records:
        if isinstance(record, dict):
            formatted_item = format_properties_with_values_multiline(record)
            formatted_items.append(formatted_item)
            formatted_items.append(separator)
    
    return "\n".join(formatted_items)

def is_empty_or_na(value: str | None) -> bool:
    """
    Check if a value is considered empty or N/A.
    
    Args:
        value: Value to check
        
    Returns:
        True if value is "0", "0.000", "N/A", empty string, or None
    """
    return value in ["0.000", "0", "N/A", "", None]

def has_meaningful_data(item: TWSEDataItem, fields: Union[str, Sequence[str]]) -> bool:
    """
    Check if any of the specified fields has meaningful (non-empty, non-N/A) data.

    Args:
        item: Dictionary to check
        fields: Single field name or list of field names to check

    Returns:
        True if ANY field has meaningful data (not "0", "N/A", etc.)
    """
    if isinstance(fields, str):
        fields = [fields]

    return any(
        not is_empty_or_na(item.get(field))
        for field in fields
    )

def filter_meaningful_fields(item: TWSEDataItem, exclude_fields: Union[str, Sequence[str], None] = None) -> TWSEDataItem:
    """
    Filter a dictionary to only include fields with meaningful values.

    Args:
        item: Dictionary to filter
        exclude_fields: Field names to exclude from output (even if they have meaningful values)

    Returns:
        New dictionary with only meaningful fields
    """
    if exclude_fields is None:
        exclude_fields = []
    elif isinstance(exclude_fields, str):
        exclude_fields = [exclude_fields]

    result = {}
    for field, value in item.items():
        if field not in exclude_fields and not is_empty_or_na(value):
            result[field] = value

    return result

def format_meaningful_fields_only(item: TWSEDataItem, exclude_fields: Union[str, Sequence[str], None] = None) -> str:
    """
    Format only fields with meaningful values as a multiline string.

    Args:
        item: Dictionary to format
        exclude_fields: Field names to exclude from output

    Returns:
        Formatted string with only meaningful fields
    """
    meaningful_data = filter_meaningful_fields(item, exclude_fields)
    return format_properties_with_values_multiline(meaningful_data)


def format_list_response(
    data: List[TWSEDataItem], 
    data_type: str,
    formatter: DataFormatter | None = None,
    limit: int = DEFAULT_DISPLAY_LIMIT
) -> str:
    """
    Format a list of records with standard header and pagination.
    
    Args:
        data: List of data records
        data_type: Description of data type for header
        formatter: Optional custom formatter function for each item
        limit: Maximum number of items to display
        
    Returns:
        Formatted string with header, items, and pagination info
        
    Example:
        >>> format_list_response(
        ...     data=brokers,
        ...     data_type="券商資料",
        ...     formatter=lambda x: f"- {x['name']} ({x['code']})"
        ... )
    """
    if not data:
        return ""
    
    result = MSG_TOTAL_RECORDS.format(count=len(data), data_type=data_type) + "\n\n"
    
    # Use default formatter if none provided
    if formatter is None:
        formatter = lambda item: f"- {format_properties_with_values_multiline(item)}\n"
    
    # Format each item up to the limit
    for item in data[:limit]:
        result += formatter(item)
    
    # Add pagination info if there are more records
    if len(data) > limit:
        result += MSG_MORE_RECORDS.format(count=len(data) - limit)
    
    return result


def create_simple_list_formatter(
    name_field: str = "名稱",
    code_field: str = "代號", 
    *extra_fields: str
) -> DataFormatter:
    """
    Create a simple formatter for list items with name, code, and optional extra fields.
    
    Args:
        name_field: Field name for the item name
        code_field: Field name for the item code
        *extra_fields: Additional field names to include
        
    Returns:
        Formatter function that formats a single item
        
    Example:
        >>> formatter = create_simple_list_formatter("券商名稱", "券商代號", "總人數")
        >>> formatter({"券商名稱": "ABC", "券商代號": "001", "總人數": "100"})
        '- ABC (001): 總人數 100\\n'
    """
    def formatter(item: TWSEDataItem) -> str:
        name = item.get(name_field, "N/A")
        code = item.get(code_field, "N/A")
        
        # Build the result starting with name and code
        result = f"- {name} ({code})"
        
        # Add extra fields if provided
        if extra_fields:
            extras = []
            for field in extra_fields:
                value = item.get(field, "N/A")
                extras.append(f"{field} {value}")
            result += ": " + ", ".join(extras)
        
        return result + "\n"
    
    return formatter