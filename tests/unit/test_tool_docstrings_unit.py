"""工具 docstring 的每一行都必須出現在 MCP 工具描述或參數說明裡（不打網路）。

FastMCP 只把 docstring 第一個 Google-style 區段之前的文字當工具描述，`Args:` 拆成各參數的說明，
其餘區段（`Returns:`、`Note:`…）整段丟掉，模型看不到。回傳內容請寫在 `Args:` 之前（`回傳：…`）。
"""

import asyncio
import inspect
import re

import pytest
from fastmcp import Client, FastMCP

from tests.helpers import _CapturingMCP
from tools import register_all_tools
from utils.api_client import TWSEAPIClient

pytestmark = pytest.mark.offline

SECTION_HEADER = re.compile(r"^[A-Z][A-Za-z ]*:$")
# `code: 股票代號` → 參數說明裡只有 `股票代號`
PARAM_PREFIX = re.compile(r"^\w+(\s*\([^)]*\))?:\s+")


def _squash(text):
    return re.sub(r"\s+", "", text)


@pytest.fixture(scope="module")
def exposed():
    mcp = FastMCP("docstring-check")
    register_all_tools(mcp, TWSEAPIClient())

    async def list_tools():
        async with Client(mcp) as client:
            return await client.list_tools()

    return {tool.name: tool.model_dump(by_alias=True) for tool in asyncio.run(list_tools())}


def test_no_docstring_text_is_dropped_from_the_tool_description(exposed):
    capturing = _CapturingMCP()
    register_all_tools(capturing, TWSEAPIClient())
    checked, dropped = 0, []
    for name, fn in capturing.tools.items():
        doc = inspect.getdoc(fn)
        if not doc:
            continue
        tool = exposed[name]
        props = (tool.get("inputSchema") or {}).get("properties", {})
        visible = _squash((tool.get("description") or "") + "".join(p.get("description", "") for p in props.values()))
        for line in doc.splitlines():
            line = line.strip()
            if not line or SECTION_HEADER.match(line):
                continue
            if _squash(PARAM_PREFIX.sub("", line)) not in visible:
                dropped.append(f"{name}: {line}")
        checked += 1
    assert checked > 100, f"只檢查到 {checked} 個工具的 docstring，自動探索可能壞了"
    assert not dropped, "docstring 內容沒有出現在工具描述裡（請移到 Args: 之前）:\n" + "\n".join(dropped)
