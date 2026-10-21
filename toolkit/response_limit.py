"""The last-resort cap on a tool reply's size: FastMCP's ResponseLimitingMiddleware, with our notice.

Tools limit their own rows (``limit`` / ``Page``), but most ``limit`` parameters have no upper bound,
so ``limit=100000`` on a list of 44,717 warrants returns 5.6 MB. Past ``max_size`` bytes (the
serialized result) the middleware keeps the leading text, cut at a UTF-8 boundary, and appends
``MSG_RESPONSE_TRUNCATED``. Error replies are raised, not returned, so they are never cut.

Pass only the text tools as ``tools``: the middleware drops the output schema of every tool it
limits from tools/list (a cut reply is text alone), so a structured tool must bound itself instead.
"""

from typing import Iterable, Optional

from fastmcp.server.middleware.response_limiting import ResponseLimitingMiddleware

from utils.constants import MSG_RESPONSE_TRUNCATED


def response_limit(max_size: int, tools: Optional[Iterable[str]] = None) -> ResponseLimitingMiddleware:
    """A ResponseLimitingMiddleware cutting replies of ``tools`` (default all) past ``max_size`` bytes."""
    return ResponseLimitingMiddleware(max_size=max_size, tools=None if tools is None else sorted(tools),
                                      truncation_suffix=MSG_RESPONSE_TRUNCATED.format(max_size=max_size))
