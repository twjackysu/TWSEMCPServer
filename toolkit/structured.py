"""Tools that return structured data alongside their text.

Such a tool declares ``@mcp.tool(output_schema=output_schema(Result))`` for a frozen dataclass
``Result`` and returns ``structured_reply(text, result)``: ``content`` keeps the text every client
reads, and ``structuredContent`` carries ``result`` for clients that use data. Once a tool declares
an output schema, every successful reply must carry conforming structured content (the MCP client
rejects one without it), so a "nothing found" outcome that has no result to give raises
``ToolError`` instead of returning text. Describe every field (unit, ROC or Gregorian):
``tests/unit/test_structured_output_unit.py`` checks that each one has a description.

The response cap (``toolkit.response_limit``) leaves these tools out — it would hide their schema
and could cut a reply down to text alone — so each one bounds its own size (e.g. ``limit``).
"""

from functools import lru_cache
from typing import Any, Dict

from fastmcp.tools import ToolResult
from fastmcp.utilities.json_schema import compress_schema
from pydantic import TypeAdapter


@lru_cache(maxsize=None)
def _adapter(result_type: type) -> TypeAdapter:
    return TypeAdapter(result_type)


def output_schema(result_type: type) -> Dict[str, Any]:
    """The JSON schema of a dataclass result, built the way FastMCP builds one from a return type."""
    return compress_schema(_adapter(result_type).json_schema(mode="serialization"), prune_titles=True)


def structured_reply(text: str, result: Any) -> ToolResult:
    """``text`` as the reply's content and ``result`` (a dataclass) as its structured content."""
    return ToolResult(content=text, structured_content=_adapter(type(result)).dump_python(result, mode="json"))
