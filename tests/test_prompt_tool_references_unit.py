"""prompts/ 內引用的工具名稱與關鍵字參數都必須真的存在（不打網路）。

prompt 模板以 `get_xxx(...)` 的字面文字指示模型呼叫哪些工具。工具被移除、改名或參數被拿掉時，
prompt 不會報錯，只會讓模型去找一個不存在的工具、或傳一個會被拒絕的參數，所以用這個測試把兩邊綁在一起。
"""

import inspect
import re
from pathlib import Path

import pytest

from tests.helpers import _CapturingMCP
from tools import register_all_tools
from utils.api_client import TWSEAPIClient

pytestmark = pytest.mark.offline

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"
# `get_xxx(...)`：只認放在反引號內、括號不巢狀的呼叫寫法
CALL_REF = re.compile(r"`(get_[a-z0-9_]+)\(([^`]*)\)`")
TOOL_NAME_REF = re.compile(r"`(get_[a-z0-9_]+)\(")
KEYWORD = re.compile(r"\b([a-z_][a-z0-9_]*)=")


@pytest.fixture(scope="module")
def registered():
    mcp = _CapturingMCP()
    register_all_tools(mcp, TWSEAPIClient())
    assert mcp.tools, "沒有註冊到任何工具，自動探索可能壞了"
    return mcp.tools


def _prompt_files():
    return sorted(PROMPTS_DIR.glob("*.py"))


def test_every_tool_named_in_prompts_is_registered(registered):
    missing = {}
    for path in _prompt_files():
        unknown = sorted(set(TOOL_NAME_REF.findall(path.read_text(encoding="utf-8"))) - set(registered))
        if unknown:
            missing[path.name] = unknown
    assert not missing, f"prompt 引用了不存在的工具: {missing}"


def test_every_keyword_argument_in_prompts_exists_on_the_tool(registered):
    bad = []
    for path in _prompt_files():
        for name, args in CALL_REF.findall(path.read_text(encoding="utf-8")):
            if name not in registered:
                continue  # 名稱錯誤由上一個測試回報
            params = set(inspect.signature(registered[name]).parameters)
            for keyword in KEYWORD.findall(args):
                if keyword not in params:
                    bad.append(f"{path.name}: {name}({keyword}=…) — 實際參數: {sorted(params)}")
    assert not bad, "prompt 使用了工具沒有的參數:\n" + "\n".join(bad)


def test_the_keyword_check_actually_catches_a_removed_parameter(registered):
    """對照組：確認上面的檢查不是空轉——已被移除的 format／count 參數必須被判為不存在."""
    params = set(inspect.signature(registered["get_market_index_info"]).parameters)
    assert {"format", "count"}.isdisjoint(params) and {"date", "category", "keyword"} <= params
    assert KEYWORD.findall('category="sector", format="summary"') == ["category", "format"]
