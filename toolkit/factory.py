"""Tool specs and the factories that register them, for the many tools that need no custom code.

A module declares its simple tools as a list of specs and registers them in a loop; every rule
those tools share (fetch, filter, paginate, wording of the empty reply, the Args section of the
description) lives here once.
"""

from dataclasses import dataclass
from typing import Callable, Optional

from fastmcp import FastMCP

from utils import (
    TWSEAPIClient,
    MSG_NO_DATA,
    MSG_NO_DATA_FOR_CODE,
    DEFAULT_DISPLAY_LIMIT,
    format_list_response,
    format_properties_with_values_multiline,
)
from utils.types import DataFormatter, TWSEDataItem

from .decorators import handle_api_errors


@dataclass(frozen=True)
class CompanyToolSpec:
    """A tool that returns one company's row of a TWSE OpenAPI list, looked up by stock code."""

    endpoint: str
    name: str
    description: str
    # Noun in the "查無…" reply when the company has no row
    empty_data_type: str = "資料"


@dataclass(frozen=True)
class ListToolSpec:
    """A tool that lists an endpoint's rows: optional ``name`` keyword filter, then pagination.

    The MCP description is ``summary`` plus a generated Args section (``name`` when
    ``filter_field`` is set, then ``limit`` / ``offset``).
    """

    endpoint: str
    name: str
    summary: str
    # Header of the list reply ("共有 N 筆{label}：")
    label: str
    # Noun in the reply when the source returns no rows at all
    empty_data_type: str
    # Renders one row (the Strategy)
    formatter: DataFormatter
    # Row field the ``name`` argument substring-filters on; None means no ``name`` argument
    filter_field: Optional[str] = None
    # How the ``name`` argument is described to the model
    name_hint: str = "名稱關鍵字（選填）"
    # Applied to every row before filtering, for sources whose rows need repairing first
    normalize: Optional[Callable[[TWSEDataItem], TWSEDataItem]] = None

    @property
    def description(self) -> str:
        lines = [self.summary, "", "        Args:"]
        if self.filter_field:
            lines.append(f"            name: {self.name_hint}")
        lines.append(f"            limit: 回傳筆數上限（預設 {DEFAULT_DISPLAY_LIMIT}）")
        lines.append("            offset: 跳過前 N 筆（預設 0，搭配 limit 分頁）")
        return "\n".join(lines)


def create_company_tool(
    mcp: FastMCP,
    spec: CompanyToolSpec,
    client: Optional[TWSEAPIClient] = None,
) -> Callable[[str], str]:
    """Register ``spec`` as a company lookup tool and return the registered function."""
    _client = client or TWSEAPIClient.get_instance()

    def tool_fn(code: str) -> str:
        data = _client.fetch_company_data(spec.endpoint, code)
        if not data:
            return MSG_NO_DATA_FOR_CODE.format(
                query_target=f"公司代號 {code}", data_type=spec.empty_data_type
            )
        return format_properties_with_values_multiline(data)

    tool_fn.__name__ = spec.name
    decorated = handle_api_errors(use_code_param=True)(tool_fn)
    mcp.tool(name=spec.name, description=spec.description)(decorated)
    return decorated


def create_list_tool(
    mcp: FastMCP,
    spec: ListToolSpec,
    client: Optional[TWSEAPIClient] = None,
) -> Callable[..., str]:
    """Register ``spec`` as a list tool and return the registered function."""
    _client = client or TWSEAPIClient.get_instance()

    def _render(data, filter_value: str, limit: int, offset: int) -> str:
        if not data:
            return MSG_NO_DATA.format(data_type=spec.empty_data_type)
        if spec.normalize:
            data = [spec.normalize(d) for d in data]
        if spec.filter_field and filter_value:
            data = [d for d in data if filter_value in d.get(spec.filter_field, "")]
        return format_list_response(data, spec.label, spec.formatter, limit=limit, offset=offset)

    if spec.filter_field:
        def tool_fn(name: str = "", limit: int = DEFAULT_DISPLAY_LIMIT, offset: int = 0) -> str:
            return _render(_client.fetch_data(spec.endpoint), name, limit, offset)
    else:
        def tool_fn(limit: int = DEFAULT_DISPLAY_LIMIT, offset: int = 0) -> str:
            return _render(_client.fetch_data(spec.endpoint), "", limit, offset)

    description = spec.description
    tool_fn.__name__ = spec.name
    tool_fn.__doc__ = description
    decorated = handle_api_errors()(tool_fn)
    mcp.tool(name=spec.name, description=description)(decorated)
    return decorated
