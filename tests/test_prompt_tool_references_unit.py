"""prompts/ 內引用的工具名稱都必須真的有註冊（不打網路）。

prompt 模板以 `get_xxx(...)` 的字面文字指示模型呼叫哪些工具。工具被移除或改名時，
prompt 不會報錯，只會讓模型去找一個不存在的工具，所以用這個測試把兩邊綁在一起。
"""

import re
from pathlib import Path

import pytest

from tests.helpers import _CapturingMCP
from tools import register_all_tools
from utils.api_client import TWSEAPIClient

pytestmark = pytest.mark.offline

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"
TOOL_REF = re.compile(r"`(get_[a-z0-9_]+)\(")


def test_every_tool_named_in_prompts_is_registered():
    mcp = _CapturingMCP()
    register_all_tools(mcp, TWSEAPIClient())
    registered = set(mcp.tools)
    assert registered, "沒有註冊到任何工具，自動探索可能壞了"

    missing = {}
    for path in sorted(PROMPTS_DIR.glob("*.py")):
        unknown = sorted(set(TOOL_REF.findall(path.read_text(encoding="utf-8"))) - registered)
        if unknown:
            missing[path.name] = unknown
    assert not missing, f"prompt 引用了不存在的工具: {missing}"
