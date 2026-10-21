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
from datetime import date
from typing import Any, Dict, Optional

import pydantic
from fastmcp.exceptions import ToolError, ValidationError
from fastmcp.server.middleware import Middleware, MiddlewareContext


# Replies keep the sources' ROC (民國) dates — 115/09/30, 115年09月30日, 1150930 — so a client that passes
# one back as a date parameter gets the Gregorian value it meant, worked out.
_ROC_SEPARATED = re.compile(r"^\s*(\d{2,3})\s*[/.\-年]\s*(\d{1,2})\s*[/.\-月]\s*(\d{1,2})\s*日?\s*$")
_ROC_COMPACT = re.compile(r"^\s*(\d{3})(\d{2})(\d{2})\s*$")
_GREGORIAN_SEPARATED = re.compile(r"^\s*(\d{4})\s*[/.\-年]\s*(\d{1,2})\s*[/.\-月]\s*(\d{1,2})\s*日?\s*$")


def _ymd(year: int, month: int, day: int) -> Optional[str]:
    try:
        return f"{date(year, month, day):%Y%m%d}"
    except ValueError:
        return None


def describe_date_mismatch(name: str, received: Any) -> str:
    """A date parameter that is not YYYYMMDD: name the Gregorian value meant when it can be worked out."""
    text = str(received)
    roc = _ROC_SEPARATED.match(text) or _ROC_COMPACT.match(text)
    if roc:
        year, month, day = (int(g) for g in roc.groups())
        meant = _ymd(year + 1911, month, day) if year <= 200 else None
        if meant:
            return (f"{name} 看起來是民國日期，請換算成西元 YYYYMMDD（民國年 + 1911）："
                    f"{text.strip()} → {meant}")
    gregorian = _GREGORIAN_SEPARATED.match(text)
    if gregorian:
        meant = _ymd(*(int(g) for g in gregorian.groups()))
        if meant:
            return f"{name} 日期格式錯誤，請使用西元 YYYYMMDD，不加分隔符號：{text.strip()} → {meant}"
    return f"{name} 日期格式錯誤，請使用西元 YYYYMMDD，例如 \"20260930\"（收到 {received!r}）"


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
    if kind == "string_pattern_mismatch":
        if r"\d{8}" in str(ctx.get("pattern", "")):  # toolkit.params.TradingDate
            return describe_date_mismatch(name, received)
        return f"{name} 格式不符（收到 {received!r}）"
    if kind == "value_error":  # an AfterValidator's ValueError, e.g. a date that does not exist
        return f"{name} {ctx.get('error')}（收到 {received!r}）"
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
