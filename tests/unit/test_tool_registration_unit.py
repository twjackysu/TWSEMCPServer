"""register_all_tools 的單元測試（不打網路）。

註冊失敗曾經只寫 log：server 照常啟動，卻悄悄少掉整個模組的工具。現在必須 fail fast。
"""

import asyncio

import pytest
from fastmcp import FastMCP

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


def test_module_that_fails_to_import_stops_registration(monkeypatch):
    monkeypatch.setattr(tools, "discover_tool_modules", lambda: ["tools.does_not_exist"])
    with pytest.raises(ModuleNotFoundError):
        tools.register_all_tools(FastMCP("probe"), OfflineClient({}))


def test_module_without_register_tools_stops_registration(monkeypatch):
    monkeypatch.setattr(tools, "discover_tool_modules", lambda: ["utils.date_helper"])
    with pytest.raises(ImportError, match="register_tools"):
        tools.register_all_tools(FastMCP("probe"), OfflineClient({}))
