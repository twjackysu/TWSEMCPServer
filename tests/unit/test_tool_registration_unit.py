"""register_all_tools 與 ToolRegistrar 的單元測試（不打網路）。

註冊失敗曾經只寫 log：server 照常啟動，卻悄悄少掉整個模組的工具。現在必須 fail fast。
FastMCP 4 會替每個 -> str 工具產生 {"result": string} 的 output schema，每次呼叫把同一份文字
在 content 與 structuredContent 各回一次；ToolRegistrar 讓文字工具不帶 output schema。
"""

import asyncio

import pytest
from fastmcp import Client, FastMCP

import tools
from tests.offline import OfflineClient

pytestmark = pytest.mark.offline


def test_every_tool_module_registers():
    """每個 tools/ 模組都能匯入並註冊；任何一個壞掉，這裡（以及 server 啟動）就會失敗."""
    mcp = FastMCP("probe")
    tools.register_all_tools(mcp, OfflineClient({}))
    registered = asyncio.run(mcp.list_tools())
    assert len(tools.discover_tool_modules()) > 50
    assert len(registered) > 100


def test_text_tools_have_no_output_schema():
    """全部工具都回傳文字；任何一個帶 output schema，就會在每次呼叫時把回應文字重複送一次."""
    mcp = FastMCP("probe")
    tools.register_all_tools(mcp, OfflineClient({}))
    with_schema = [t.name for t in asyncio.run(mcp.list_tools()) if t.output_schema is not None]
    assert with_schema == []


def _registrar_probe():
    mcp = FastMCP("probe")
    registrar = tools.ToolRegistrar(mcp)

    @registrar.tool
    def bare() -> str:
        return "bare"

    def renamed() -> str:
        return "renamed"

    registrar.tool(name="custom_name", description="說明")(renamed)

    @registrar.tool("positional_name")
    def positional() -> str:
        return "positional"

    @registrar.tool(output_schema={"type": "object", "properties": {"x": {"type": "string"}}})
    def explicit() -> str:
        return "explicit"

    @registrar.tool
    def structured() -> dict:
        return {"x": 1}

    return mcp


def test_registrar_supports_every_call_form_and_drops_text_output_schema():
    mcp = _registrar_probe()
    found = {t.name: t for t in asyncio.run(mcp.list_tools())}
    assert set(found) == {"bare", "custom_name", "positional_name", "explicit", "structured"}
    assert found["custom_name"].description == "說明"
    for name in ("bare", "custom_name", "positional_name"):
        assert found[name].output_schema is None, name


def test_registrar_keeps_explicit_and_non_text_output_schemas():
    found = {t.name: t for t in asyncio.run(_registrar_probe().list_tools())}
    assert found["explicit"].output_schema["properties"] == {"x": {"type": "string"}}
    assert found["structured"].output_schema is not None


def test_text_tool_reply_is_sent_once():
    async def call():
        async with Client(_registrar_probe()) as client:
            return await client.call_tool("bare", {})

    result = asyncio.run(call())
    assert result.content[0].text == "bare"
    assert result.structured_content is None


def test_module_that_fails_to_import_stops_registration(monkeypatch):
    monkeypatch.setattr(tools, "discover_tool_modules", lambda: ["tools.does_not_exist"])
    with pytest.raises(ModuleNotFoundError):
        tools.register_all_tools(FastMCP("probe"), OfflineClient({}))


def test_module_without_register_tools_stops_registration(monkeypatch):
    monkeypatch.setattr(tools, "discover_tool_modules", lambda: ["utils.date_helper"])
    with pytest.raises(ImportError, match="register_tools"):
        tools.register_all_tools(FastMCP("probe"), OfflineClient({}))
