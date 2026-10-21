"""結構化輸出（toolkit.structured）的單元測試（不打網路）。

選股、同業比較、還原日K、技術指標的回覆：content 仍是原本的文字，structuredContent 是 dataclass，
outputSchema 由 dataclass 產生。client 會依 schema 驗證 structuredContent，所以這裡透過 Client 呼叫。
"""

import asyncio
from dataclasses import dataclass
from typing import Annotated, List, Optional

import pytest
from fastmcp import Client, FastMCP
from fastmcp.exceptions import ToolError
from pydantic import Field

import tools
from tests.offline import OfflineClient
from tests.unit.test_screening_unit import _routes
from toolkit import output_schema, structured_reply

pytestmark = pytest.mark.offline


def _server():
    mcp = FastMCP("probe")
    registered = tools.register_all_tools(mcp, OfflineClient(_routes({})))
    return mcp, registered


def _properties(schema):
    """(path, property schema) for every property, nested definitions included."""
    for name, prop in schema.get("properties", {}).items():
        yield name, prop
    for model, definition in schema.get("$defs", {}).items():
        for name, prop in definition.get("properties", {}).items():
            yield f"{model}.{name}", prop


def test_every_field_of_a_structured_result_is_described():
    """欄位名稱是英文；單位（元、股、%）與民國／西元只寫在說明裡，所以每個欄位都要有說明."""
    mcp, registered = _server()
    undescribed = []
    for tool in asyncio.run(mcp.list_tools()):
        if tool.name in registered.structured:
            assert tool.output_schema["type"] == "object"
            undescribed += [f"{tool.name}: {path}" for path, prop in _properties(tool.output_schema)
                            if not prop.get("description")]
    assert undescribed == []


def test_a_structured_reply_passes_the_client_s_schema_validation():
    mcp, _ = _server()

    async def call():
        async with Client(mcp) as client:
            return await client.call_tool("get_industry_peers", {"code": "6488", "limit": 1})

    result = asyncio.run(call())  # the client raises if structuredContent does not match outputSchema
    assert result.structured_content["code"] == "6488" and "▶ 6488" in result.content[0].text
    assert result.data.peers[1].code == "6488"  # FastMCP's client rebuilds the result from the schema


def test_nothing_to_return_is_an_error_reply():
    mcp, _ = _server()

    async def call():
        async with Client(mcp) as client:
            return await client.call_tool("get_industry_peers", {"code": "9999"}, raise_on_error=False)

    result = asyncio.run(call())
    assert result.is_error and result.content[0].text.startswith("查無 9999 的產業別")


def test_a_limit_above_the_bound_is_rejected():
    """結構化回覆不受回應大小上限保護，筆數由 schema 擋."""
    mcp, _ = _server()

    async def call():
        async with Client(mcp) as client:
            await client.call_tool("get_stock_screener", {"limit": 501})

    with pytest.raises(ToolError, match="limit"):
        asyncio.run(call())


@dataclass(frozen=True)
class _Row:
    """A row."""

    code: Annotated[str, Field(description="代號")]
    close: Annotated[Optional[float], Field(description="收盤價（元）")] = None


@dataclass(frozen=True)
class _Result:
    """A result."""

    rows: Annotated[List[_Row], Field(description="列")]


def test_output_schema_matches_what_fastmcp_derives_from_a_return_type():
    mcp = FastMCP("probe")

    @mcp.tool
    def derived() -> _Result:
        return _Result([])

    assert output_schema(_Result) == asyncio.run(mcp.get_tool("derived")).output_schema


def test_structured_reply_keeps_the_text_and_serializes_the_data():
    reply = structured_reply("文字", _Result([_Row("2330", 1450.0), _Row("6488")]))
    assert [b.text for b in reply.content] == ["文字"]
    assert reply.structured_content == {"rows": [{"code": "2330", "close": 1450.0}, {"code": "6488", "close": None}]}
