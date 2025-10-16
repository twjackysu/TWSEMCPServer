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