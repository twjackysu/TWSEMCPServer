"""Data formatting utilities."""

from typing import Dict, Any, List

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