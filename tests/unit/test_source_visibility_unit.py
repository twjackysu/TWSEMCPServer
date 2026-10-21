"""依資料來源開關工具（tools.enabled_sources／show_only_sources，FastMCP Visibility），不打網路。

部署時可用 TWSE_INCLUDE_SOURCES／TWSE_EXCLUDE_SOURCES 只開一部分來源（例如不開期貨）：
工具只要讀到一個沒開的來源就從 tools/list 消失、呼叫時是未知工具；prompt 只要還有一個來源開著就保留。
"""

import asyncio
import inspect
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest
from fastmcp import Client, FastMCP
from fastmcp.exceptions import ToolError

import server
import tools
from tests.offline import OfflineClient

pytestmark = pytest.mark.offline

ROOT = Path(__file__).resolve().parents[2]
ALL = frozenset(tools.SOURCES)
TOOL_NAME_REF = re.compile(r"`(get_[a-z0-9_]+)\(")


def _server(sources):
    mcp = FastMCP("probe")
    tools.register_all_tools(mcp, OfflineClient({}))
    tools.show_only_sources(mcp, frozenset(sources))
    return mcp


def _listed(sources):
    return {t.name for t in asyncio.run(_server(sources).list_tools())}


@pytest.fixture(scope="module")
def tags():
    """Every tool's source tags, with every source served."""
    return {t.name: t.tags for t in asyncio.run(_server(ALL).list_tools())}


def test_enabled_sources_reads_include_then_exclude():
    assert tools.enabled_sources() == ALL
    assert tools.enabled_sources(" twse, TPEX ,") == {"twse", "tpex"}
    assert tools.enabled_sources(exclude="taifex") == ALL - {"taifex"}
    assert tools.enabled_sources("twse,tpex,taifex", "taifex") == {"twse", "tpex"}


def test_an_unknown_source_or_nothing_left_is_an_error():
    """打錯字不能默默把工具藏起來，全部排除也不能啟動一個沒有工具的 server."""
    with pytest.raises(ValueError, match=r"unknown data source\(s\) \['tsmc'\]"):
        tools.enabled_sources("twse,tsmc")
    with pytest.raises(ValueError, match="unknown data source"):
        tools.enabled_sources(exclude="futures")
    with pytest.raises(ValueError, match="every data source is excluded"):
        tools.enabled_sources("tdcc", "tdcc")


def test_serving_every_source_hides_nothing(tags):
    unfiltered = FastMCP("probe")
    tools.register_all_tools(unfiltered, OfflineClient({}))
    assert set(tags) == {t.name for t in asyncio.run(unfiltered.list_tools())}


def test_a_tool_is_hidden_when_any_source_it_reads_is_off(tags):
    listed = _listed(ALL - {"tpex"})
    assert listed == {name for name, t in tags.items() if "tpex" not in t}
    assert {"get_otc_institutional", "get_etf_info", "get_stock_screener"}.isdisjoint(listed)  # tpex, +sitca/twse, +twse
    assert {"get_twse_institutional_investors_summary", "get_etf_holdings", "get_put_call_ratio"} <= listed


def test_only_the_tools_that_need_nothing_else_remain(tags):
    listed = _listed({"twse"})
    assert listed == {name for name, t in tags.items() if t == {"twse"}}
    assert "get_stock_screener" not in listed and "get_company_profile" in listed


def test_calling_a_hidden_tool_fails_as_an_unknown_tool():
    async def call():
        async with Client(_server(ALL - {"taifex"})) as client:
            await client.call_tool("get_put_call_ratio", {})

    with pytest.raises(ToolError, match="Unknown tool"):
        asyncio.run(call())


def test_prompt_tags_are_the_sources_of_the_tools_they_name(tags):
    """prompt 的 tags（server.py）必須等於它點名的工具的來源聯集，開關來源時它才會跟著工具走."""
    prompts = asyncio.run(server.mcp.list_prompts())
    assert len(prompts) == 9
    wrong = {}
    for prompt in prompts:
        builder = getattr(server, re.search(r"return (\w+)\(", inspect.getsource(prompt.fn)).group(1))
        text = Path(inspect.getsourcefile(builder)).read_text(encoding="utf-8")
        needed = set().union(*(tags[name] for name in TOOL_NAME_REF.findall(text)))
        if prompt.tags != needed:
            wrong[prompt.name] = {"declared": sorted(prompt.tags), "named tools read": sorted(needed)}
    assert wrong == {}


# The real server, configured from the environment: run in a fresh interpreter, since server.py reads
# the settings when it is imported.
_PROBE = """
import asyncio, json, logging
logging.disable(logging.CRITICAL)
from fastmcp import Client
import server

async def main():
    async with Client(server.mcp) as client:
        return {"tools": sorted(t.name for t in await client.list_tools()),
                "prompts": sorted(p.name for p in await client.list_prompts()),
                "instructions": client.instructions}

print(json.dumps(asyncio.run(main()), ensure_ascii=False))
"""


def _run_server(**settings):
    env = {k: v for k, v in os.environ.items() if k not in ("TWSE_INCLUDE_SOURCES", "TWSE_EXCLUDE_SOURCES")}
    env.update(settings, PYTHONIOENCODING="utf-8")
    return subprocess.run([sys.executable, "-c", _PROBE], cwd=ROOT, env=env, capture_output=True, text=True,
                          encoding="utf-8", timeout=120)


def test_server_without_futures(tags):
    result = _run_server(TWSE_EXCLUDE_SOURCES="taifex")
    assert result.returncode == 0, result.stderr
    served = json.loads(result.stdout)
    assert set(served["tools"]) == {name for name, t in tags.items() if "taifex" not in t}
    assert "taifex_derivatives" not in served["prompts"]
    assert "institutional_flow" in served["prompts"]  # still has its twse/tpex/mops/tdcc tools
    assert served["instructions"].startswith(
        "台灣證券市場資料：證交所、櫃買中心、公開資訊觀測站、集保結算所、投信投顧公會、國發會、中央銀行。\n")


def test_server_with_futures_only(tags):
    result = _run_server(TWSE_INCLUDE_SOURCES="taifex")
    assert result.returncode == 0, result.stderr
    served = json.loads(result.stdout)
    assert set(served["tools"]) == {name for name, t in tags.items() if t == {"taifex"}}
    assert served["prompts"] == ["institutional_flow", "taifex_derivatives"]
    assert served["instructions"].startswith("台灣證券市場資料：期交所。\n")


def test_server_refuses_an_unknown_source():
    result = _run_server(TWSE_EXCLUDE_SOURCES="futures")
    assert result.returncode != 0
    assert "unknown data source(s) ['futures']" in result.stderr


def test_default_instructions_name_every_source():
    assert server.SERVED_SOURCES == ALL
    assert server.SERVER_INSTRUCTIONS.startswith(
        "台灣證券市場資料：證交所、櫃買中心、期交所、公開資訊觀測站、集保結算所、投信投顧公會、國發會、中央銀行。\n")
