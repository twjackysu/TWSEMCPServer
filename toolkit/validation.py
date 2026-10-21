"""Argument validation errors in the tools' language.

FastMCP validates a call's arguments against the tool's schema (toolkit/params.py) before the tool
runs and reports a mismatch with pydantic's English text ("Input should be 'total' or 'foreign'
[type=literal_error, ...]"). ``ArgumentErrorsInChinese`` catches that rejection in the middleware
chain — where it is still a ``fastmcp.exceptions.ValidationError`` with pydantic's structured
errors as its cause — and raises a ``ToolError`` that says the same in Chinese, the way every
other tool message reads. Errors raised by a tool body never get here as ValidationError: they
are already ``ToolError`` (toolkit/decorators.py).
"""

import re
from typing import Any, Dict

import pydantic
from fastmcp.exceptions import ToolError, ValidationError
from fastmcp.server.middleware import Middleware, MiddlewareContext


def describe(error: Dict[str, Any]) -> str:
    """One pydantic error as a Chinese sentence naming the parameter."""
    name = ".".join(str(part) for part in error.get("loc", ())) or "參數"
    kind, ctx, received = error.get("type", ""), error.get("ctx") or {}, error.get("input")
    if kind == "literal_error":
        # ctx["expected"] reads "'total', 'foreign' or 'dealer'" (strings) or "1, 5 or 15" (ints)
        values = [text if not number else number
                  for text, number in re.findall(r"'([^']*)'|(-?\d+)", str(ctx.get("expected", "")))]
        choices = "、".join(v if v != "" else "（留空）" for v in values)
        return f"{name} 只能是 {choices}（收到 {received!r}）"
    if kind in ("greater_than_equal", "greater_than"):
        bound = ctx.get("ge", ctx.get("gt"))
        return f"{name} 不可小於 {bound}（收到 {received!r}）" if kind == "greater_than_equal" else f"{name} 必須大於 {bound}（收到 {received!r}）"
    if kind in ("less_than_equal", "less_than"):
        bound = ctx.get("le", ctx.get("lt"))
        return f"{name} 不可大於 {bound}（收到 {received!r}）" if kind == "less_than_equal" else f"{name} 必須小於 {bound}（收到 {received!r}）"
    if kind.startswith("int_"):
        return f"{name} 必須是整數（收到 {received!r}）"
    if kind.startswith("bool_"):
        return f"{name} 必須是 true 或 false（收到 {received!r}）"
    if kind.startswith("string_"):
        return f"{name} 必須是文字（收到 {received!r}）"
    if kind == "missing" or kind == "missing_argument":
        return f"缺少必填參數 {name}"
    if kind in ("unexpected_keyword_argument", "extra_forbidden"):
        return f"沒有 {name} 這個參數"
    return f"{name} 不正確：{error.get('msg', kind)}"


class ArgumentErrorsInChinese(Middleware):
    """Re-raise FastMCP's argument-validation error as a ToolError worded in Chinese."""

    async def on_call_tool(self, context: MiddlewareContext, call_next):
        try:
            return await call_next(context)
        except ValidationError as e:
            cause = e.__cause__
            if not isinstance(cause, pydantic.ValidationError):
                raise
            raise ToolError("；".join(describe(err) for err in cause.errors())) from e
