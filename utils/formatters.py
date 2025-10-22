"""Data formatting utilities."""

from typing import Dict, Any, List, Union

def format_properties_with_values_multiline(data: Dict[str, Any]) -> str:
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

def format_multiple_records(records: List[Dict[str, Any]], separator: str = "-" * 30) -> str:
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

def is_empty_or_na(value: Any) -> bool:
    """
    Check if a value is considered empty or N/A.
    
    Args:
        value: Value to check
        
    Returns:
        True if value is "0", "0.000", "N/A", empty string, or None
    """
    return value in ["0.000", "0", "N/A", "", None]

def has_meaningful_data(item: Dict[str, Any], fields: Union[str, List[str]]) -> bool:
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

def filter_meaningful_fields(item: Dict[str, Any], exclude_fields: Union[str, List[str], None] = None) -> Dict[str, Any]:
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

def format_meaningful_fields_only(item: Dict[str, Any], exclude_fields: Union[str, List[str], None] = None) -> str:
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