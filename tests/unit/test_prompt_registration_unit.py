"""prompts.register_all_prompts 的單元測試（不打網路）。

prompts/ 下每個模組放一個 prompt（唯一的公開函式：名稱＝prompt 名稱、docstring＝說明、參數＝引數），
自動發現註冊，server.py 不再逐一列出。prompt 的 tags 由它點名的工具（`get_xxx(...)`）的來源算出，
依來源開關工具時（tools.show_only_sources）prompt 才會跟著它的工具走。
"""

import asyncio
import importlib
import inspect
import types

import pytest
from fastmcp import FastMCP

import prompts
import server

pytestmark = pytest.mark.offline

# What clients see: renaming a prompt breaks whoever picks it by name.
PROMPT_NAMES = {
    "stock_trend_analysis_prompt", "foreign_investment_analysis", "market_hotspot_monitoring",
    "dividend_investment_strategy", "investment_screening", "taifex_derivatives", "institutional_flow",
    "company_fundamental_healthcheck", "pre_trade_risk_scan",
}


@pytest.fixture(scope="module")
def registered():
    return {p.name: p for p in asyncio.run(server.mcp.list_prompts())}


def test_every_prompt_module_is_registered(registered):
    assert set(registered) == PROMPT_NAMES
    assert len(prompts.discover_prompt_modules()) == len(PROMPT_NAMES)


def test_a_prompt_is_its_module_s_function(registered):
    """名稱、說明、引數都直接來自函式本身."""
    for module_path in prompts.discover_prompt_modules():
        fn = prompts.prompt_of(importlib.import_module(module_path))
        prompt = registered[fn.__name__]
        assert prompt.description == inspect.getdoc(fn), module_path
        assert [a.name for a in prompt.arguments] == list(inspect.signature(fn).parameters), module_path


def test_prompt_tags_come_from_the_tools_they_name(registered):
    assert registered["taifex_derivatives"].tags == {"taifex"}
    assert registered["institutional_flow"].tags == {"twse", "tpex", "taifex", "mops", "tdcc"}
    assert registered["pre_trade_risk_scan"].tags == {"twse", "tpex", "mops"}


def test_tags_are_the_union_of_the_named_tools_sources():
    tool_tags = {"get_a": frozenset({"twse"}), "get_b": frozenset({"twse", "tpex"}), "get_c": frozenset({"taifex"})}
    text = "先呼叫 `get_a()`，再 `get_b(code=\"2330\")`；get_c 沒有反引號、不算點名。"
    assert prompts.prompt_tags(text, tool_tags) == {"twse", "tpex"}
    assert prompts.prompt_tags("沒有點名任何工具", tool_tags) == frozenset()


def test_naming_an_unregistered_tool_is_an_error():
    with pytest.raises(LookupError, match=r"\['get_gone'\]"):
        prompts.prompt_tags("`get_a()` `get_gone()`", {"get_a": frozenset({"twse"})})


def test_registration_stops_on_a_prompt_naming_an_unregistered_tool():
    with pytest.raises(LookupError, match=r"prompts\.\w+: prompt names tools that are not registered"):
        prompts.register_all_prompts(FastMCP("probe"), {})


def _module(code: str) -> types.ModuleType:
    module = types.ModuleType("prompts.probe")
    exec(code, module.__dict__)
    return module


def test_a_prompt_module_defines_exactly_one_public_function():
    assert prompts.prompt_of(_module("from textwrap import dedent\ndef _helper(): pass\ndef p() -> str: return ''")).__name__ == "p"
    with pytest.raises(ImportError, match="exactly one public function"):
        prompts.prompt_of(_module("x = 1"))
    with pytest.raises(ImportError, match=r"\['p', 'q'\]"):
        prompts.prompt_of(_module("def p() -> str: return ''\ndef q() -> str: return ''"))
