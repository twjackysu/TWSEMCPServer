"""參數錯誤必須 raise ToolError，不可當一般文字 return（不打網路）。

當文字回傳時 MCP 的 isError=false：client 只能讀文字猜這次呼叫是否失敗。這裡掃描每個工具函式
（@mcp.tool / @handle_api_errors）以及它直接呼叫的模組內 helper，找出回傳參數錯誤訊息的 return。
「查無…」是正常回應，不算。
"""

import ast
import pathlib

import pytest

pytestmark = pytest.mark.offline

TOOLS_DIR = pathlib.Path(__file__).resolve().parents[2] / "tools"
# 參數錯誤訊息的固定說法（訊息內容見各工具）
ARGUMENT_ERROR_WORDS = ("必須是", "只能是", "必須介於", "格式錯誤", "不可晚於", "同時指定", "請提供", "不可超過")


def _text(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        return "".join(v.value for v in node.values if isinstance(v, ast.Constant))
    return None


def _is_tool(fn: ast.FunctionDef) -> bool:
    for d in fn.decorator_list:
        name = ast.unparse(d.func if isinstance(d, ast.Call) else d)
        if name in ("mcp.tool", "handle_api_errors"):
            return True
    return False


def _argument_error_returns(path: pathlib.Path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for fn in ast.walk(tree):
        if not isinstance(fn, ast.FunctionDef) or not _is_tool(fn):
            continue
        for node in ast.walk(fn):
            if not isinstance(node, ast.Return) or node.value is None:
                continue
            text = _text(node.value)
            if isinstance(node.value, ast.Name) and node.value.id == "error":
                yield node.lineno, "return error"
            elif text and any(w in text for w in ARGUMENT_ERROR_WORDS) and "查無" not in text:
                yield node.lineno, text[:40]


def test_tools_raise_argument_errors():
    offenders = [
        f"{path.relative_to(TOOLS_DIR.parent)}:{line}  {what}"
        for path in sorted(TOOLS_DIR.rglob("*.py"))
        for line, what in _argument_error_returns(path)
    ]
    assert offenders == [], "參數錯誤要 raise ToolError(訊息)，不要 return：\n" + "\n".join(offenders)
