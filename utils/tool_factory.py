"""Factory functions for creating MCP tools with reduced boilerplate."""

from typing import Callable, Optional
from fastmcp import FastMCP
from utils import (
    TWSEAPIClient,
    MSG_NO_DATA,
    format_list_response,
    format_properties_with_values_multiline,
)
from utils.decorators import handle_api_errors
from utils.types import DataFormatter

def create_company_tool(mcp: FastMCP, endpoint: str, name: str, docstring: str, client: Optional[TWSEAPIClient] = None) -> Callable[[str], str]:
    """
    Create and register a standard company data query tool.

    Args:
        mcp: FastMCP instance
        endpoint: TWSE API endpoint (e.g., "/opendata/t187ap46_L_9")
        name: Function name for the tool
        docstring: Tool description
        client: TWSEAPIClient instance for dependency injection

    Returns:
        The registered tool function
    """
    _client = client or TWSEAPIClient.get_instance()

    def tool_fn(code: str) -> str:
        data = _client.fetch_company_data(endpoint, code)
        return format_properties_with_values_multiline(data) if data else ""

    tool_fn.__name__ = name
    decorated = handle_api_errors(use_code_param=True)(tool_fn)
    mcp.tool(name=name, description=docstring)(decorated)
    return decorated


def create_list_tool(
    mcp: FastMCP,
    endpoint: str,
    name: str,
    docstring: str,
    label: str,
    empty_data_type: str,
    formatter: DataFormatter,
    filter_field: Optional[str] = None,
    client: Optional[TWSEAPIClient] = None,
) -> Callable[..., str]:
    """
    Create and register a standard list-style market/company query tool.

    Collapses the ubiquitous "fetch list → optional name filter → paginate"
    boilerplate. The per-tool rendering rule is supplied as ``formatter``
    (Strategy), while everything else is declared via the arguments below.

    Args:
        mcp: FastMCP instance
        endpoint: TWSE API endpoint (passed to ``fetch_data``)
        name: Function name for the registered tool
        docstring: Tool description (also the MCP schema description)
        label: Header label passed to ``format_list_response``
        empty_data_type: ``data_type`` for the MSG_NO_DATA message when the
            source returns no rows at all
        formatter: Per-item rendering function (the Strategy)
        filter_field: When set, the tool exposes a ``name`` keyword that
            substring-filters rows on this field; when None, the tool only
            exposes ``limit``/``offset``
        client: TWSEAPIClient instance for dependency injection

    Returns:
        The registered tool function
    """
    _client = client or TWSEAPIClient.get_instance()

    def _render(data, filter_value: str, limit: int, offset: int) -> str:
        if not data:
            return MSG_NO_DATA.format(data_type=empty_data_type)
        if filter_field and filter_value:
            data = [d for d in data if filter_value in d.get(filter_field, "")]
        return format_list_response(data, label, formatter, limit=limit, offset=offset)

    if filter_field:
        def tool_fn(name: str = "", limit: int = 50, offset: int = 0) -> str:
            return _render(_client.fetch_data(endpoint), name, limit, offset)
    else:
        def tool_fn(limit: int = 50, offset: int = 0) -> str:
            return _render(_client.fetch_data(endpoint), "", limit, offset)

    tool_fn.__name__ = name
    tool_fn.__doc__ = docstring
    decorated = handle_api_errors()(tool_fn)
    mcp.tool(name=name, description=docstring)(decorated)
    return decorated
