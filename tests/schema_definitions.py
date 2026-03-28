"""Schema definitions sourced from TWSE Swagger.

The TWSE swagger response schemas often describe the array item shape directly
as an object with properties, even when the actual API returns a top-level
JSON array. Tests should therefore compare live response item fields against
the swagger item schema, not treat the swagger schema as a top-level object
response.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Dict, List

import requests


_REPO_ROOT = Path(__file__).resolve().parents[1]
_LOCAL_SWAGGER_PATH = _REPO_ROOT / "staticFiles" / "swagger_decoded.json"
_SWAGGER_URL = "https://openapi.twse.com.tw/v1/swagger.json"


def _extract_properties(response_schema: dict | None) -> List[str]:
    """Extract item field names from a swagger response schema.

    TWSE swagger sometimes omits the top-level array declaration and documents
    only the array item's properties. If a proper array schema is present, use
    its items schema; otherwise treat the response schema itself as the item
    schema.
    """
    if not response_schema:
        return []

    item_schema = response_schema
    if response_schema.get("type") == "array" and isinstance(response_schema.get("items"), dict):
        item_schema = response_schema["items"]

    properties = item_schema.get("properties", {})
    return list(properties.keys()) if isinstance(properties, dict) else []


def _build_schema_map(swagger_data: dict) -> Dict[str, List[str]]:
    paths = swagger_data.get("paths", {})
    schema_map: Dict[str, List[str]] = {}

    for endpoint, path_info in paths.items():
        get_info = path_info.get("get") if isinstance(path_info, dict) else None
        if not isinstance(get_info, dict):
            continue

        response_200 = get_info.get("responses", {}).get("200", {})
        schema = response_200.get("schema") if isinstance(response_200, dict) else None
        fields = _extract_properties(schema)
        if fields:
            schema_map[endpoint] = fields

    return schema_map


@lru_cache(maxsize=1)
def _load_swagger_schema_map() -> Dict[str, List[str]]:
    try:
        response = requests.get(_SWAGGER_URL, timeout=60, verify=False)
        response.raise_for_status()
        return _build_schema_map(response.json())
    except Exception:
        return _build_schema_map(json.loads(_LOCAL_SWAGGER_PATH.read_text(encoding="utf-8")))

API_SCHEMA_MAP: Dict[str, List[str]] = _load_swagger_schema_map()


def get_required_fields(endpoint: str) -> List[str]:
    """Get required fields for an API endpoint.
    
    Args:
        endpoint: API endpoint path
        
    Returns:
        List of required field names
        
    Raises:
        KeyError: If endpoint is not in schema map
    """
    if endpoint not in API_SCHEMA_MAP:
        raise KeyError(f"Endpoint {endpoint} not found in schema map. Please add it to API_SCHEMA_MAP.")
    
    return API_SCHEMA_MAP[endpoint]


def get_all_endpoints() -> List[str]:
    """Get list of all monitored API endpoints."""
    return sorted(API_SCHEMA_MAP.keys())
