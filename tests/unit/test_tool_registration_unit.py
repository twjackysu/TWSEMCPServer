"""register_all_tools 與 ToolRegistrar 的單元測試（不打網路）。

註冊失敗曾經只寫 log：server 照常啟動，卻悄悄少掉整個模組的工具。現在必須 fail fast。
FastMCP 4 會替每個 -> str 工具產生 {"result": string} 的 output schema，每次呼叫把同一份文字
在 content 與 structuredContent 各回一次；ToolRegistrar 讓文字工具不帶 output schema。
ToolRegistrar 也替每個工具加上唯讀 annotations 與資料來源 tags（tools.SOURCE_TAGS）。
"""

import asyncio
from pathlib import Path

import pytest
from fastmcp import Client, FastMCP
from mcp.types import ToolAnnotations

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


def _registered_tools():
    mcp = FastMCP("probe")
    tools.register_all_tools(mcp, OfflineClient({}))
    return asyncio.run(mcp.list_tools())


def test_every_tool_is_annotated_read_only():
    """全部工具都只讀公開資料：client 可據此免確認、並行呼叫."""
    not_read_only = [t.name for t in _registered_tools() if t.annotations != tools.READ_ONLY]
    assert not_read_only == []
    assert (tools.READ_ONLY.read_only_hint, tools.READ_ONLY.destructive_hint, tools.READ_ONLY.idempotent_hint,
            tools.READ_ONLY.open_world_hint) == (True, False, True, True)


def test_every_tool_is_tagged_with_known_sources():
    untagged = {t.name: t.tags for t in _registered_tools() if not t.tags or not t.tags <= set(tools.SOURCES)}
    assert untagged == {}


def test_tags_follow_the_module_s_sources():
    by_name = {t.name: t.tags for t in _registered_tools()}
    assert by_name["get_otc_institutional"] == {"tpex"}
    assert by_name["get_twse_institutional_investors_summary"] == {"twse"}
    assert by_name["get_company_dividend"] == {"mops"}
    assert by_name["get_etf_info"] == {"sitca", "twse", "tpex"}
    assert by_name["get_stock_screener"] == {"twse", "tpex"}
    assert by_name["get_company_profile"] == {"twse"}  # an OpenAPI spec tool (create_company_tool)
    assert by_name["get_exchange_rates"] == {"cbc"}


# Where a module's code reaches a source, its tags must name that source (a module that starts calling
# TPEx but stays tagged twse alone would hide from a tpex filter).
_HOSTS = {"mops.twse.com.tw": "mops", "mopsov.twse.com.tw": "mops", "tpex.org.tw": "tpex",
          "taifex.com.tw": "taifex", "tdcc.com.tw": "tdcc", "sitca.org.tw": "sitca", "ndc.gov.tw": "ndc",
          "cbc.gov.tw": "cbc"}
_HELPERS = {"utils.mops": "mops", "utils.sitca": "sitca", "utils.taifex": "taifex", "sources.tpex": "tpex",
            "TPEX_WWW": "tpex", "services.price_series": "tpex", "services.market_snapshot": "tpex"}


def test_source_tags_cover_what_each_module_reaches():
    missing = {}
    for module in tools.discover_tool_modules():
        text = Path(module.replace(".", "/") + ".py").read_text(encoding="utf-8")
        needed = {tag for host, tag in _HOSTS.items() if host in text}
        needed |= {tag for marker, tag in _HELPERS.items() if marker in text}
        if "twse.com.tw" in text.replace("mops.twse.com.tw", "").replace("mopsov.twse.com.tw", "") \
                or "fetch_data(" in text or "fetch_company_data(" in text or "Spec(" in text \
                or "sources.twse" in text or "services." in text:
            needed.add("twse")
        if not needed <= tools.source_tags(module):
            missing[module] = needed - tools.source_tags(module)
    assert missing == {}


def test_a_module_without_source_tags_is_an_error():
    with pytest.raises(LookupError, match="SOURCE_TAGS"):
        tools.source_tags("tools.newsource.quotes")
    assert tools.source_tags("tools.etf.info") == {"sitca", "twse", "tpex"}  # the longest prefix wins
    assert tools.source_tags("tools.otc.history") == {"tpex"}


def test_explicit_annotations_and_tags_win():
    mcp = FastMCP("probe")
    registrar = tools.ToolRegistrar(mcp, tags=frozenset({"twse"}))

    @registrar.tool(tags={"tpex"}, annotations=ToolAnnotations(read_only_hint=True, open_world_hint=False))
    def special() -> str:
        return "x"

    @registrar.tool
    def plain() -> str:
        return "y"

    found = {t.name: t for t in asyncio.run(mcp.list_tools())}
    assert found["special"].tags == {"tpex"} and found["special"].annotations.open_world_hint is False
    assert found["plain"].tags == {"twse"} and found["plain"].annotations == tools.READ_ONLY


def test_register_all_tools_returns_every_tool_s_tags():
    """prompts 依這份對照表算出自己的 tags：必須和真正註冊的工具一模一樣."""
    mcp = FastMCP("probe")
    returned = tools.register_all_tools(mcp, OfflineClient({}))
    assert returned == {t.name: t.tags for t in asyncio.run(mcp.list_tools())}


def test_registrar_records_the_final_name_and_tags():
    mcp = FastMCP("probe")
    registered = {}
    registrar = tools.ToolRegistrar(mcp, tags=frozenset({"twse"}), registered=registered)

    @registrar.tool
    def bare() -> str:
        return "x"

    @registrar.tool("positional_name")
    def positional() -> str:
        return "x"

    @registrar.tool(name="keyword_name", tags={"tpex"})
    def keyword() -> str:
        return "x"

    assert registered == {"bare": {"twse"}, "positional_name": {"twse"}, "keyword_name": {"tpex"}}
    assert registered == {t.name: t.tags for t in asyncio.run(mcp.list_tools())}


def test_annotations_and_tags_reach_the_client():
    async def listed():
        async with Client(_registrar_probe_with_tags()) as client:
            return await client.list_tools()

    tool = asyncio.run(listed())[0]
    assert tool.annotations.read_only_hint is True and tool.annotations.destructive_hint is False
    assert tool.meta["fastmcp"]["tags"] == ["twse"]


def _registrar_probe_with_tags():
    mcp = FastMCP("probe")

    @tools.ToolRegistrar(mcp, tags=frozenset({"twse"})).tool
    def probe() -> str:
        return "x"

    return mcp


def test_module_that_fails_to_import_stops_registration(monkeypatch):
    monkeypatch.setattr(tools, "discover_tool_modules", lambda: ["tools.does_not_exist"])
    with pytest.raises(ModuleNotFoundError):
        tools.register_all_tools(FastMCP("probe"), OfflineClient({}))


def test_module_without_register_tools_stops_registration(monkeypatch):
    monkeypatch.setattr(tools, "discover_tool_modules", lambda: ["utils.date_helper"])
    with pytest.raises(ImportError, match="register_tools"):
        tools.register_all_tools(FastMCP("probe"), OfflineClient({}))
