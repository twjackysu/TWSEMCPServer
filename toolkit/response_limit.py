"""The last-resort cap on a tool reply's size: FastMCP's ResponseLimitingMiddleware, with our notice.

Tools limit their own rows (``limit`` / ``Page``), but most ``limit`` parameters have no upper bound,
so ``limit=100000`` on a list of 44,717 warrants returns 5.6 MB. Past ``max_size`` bytes (the
serialized result) the middleware keeps the leading text, cut at a UTF-8 boundary, and appends
``MSG_RESPONSE_TRUNCATED``. Error replies are raised, not returned, so they are never cut.
"""

from fastmcp.server.middleware.response_limiting import ResponseLimitingMiddleware

from utils.constants import MSG_RESPONSE_TRUNCATED


def response_limit(max_size: int) -> ResponseLimitingMiddleware:
    """A ResponseLimitingMiddleware cutting replies past ``max_size`` bytes, with the Chinese notice."""
    return ResponseLimitingMiddleware(max_size=max_size,
                                      truncation_suffix=MSG_RESPONSE_TRUNCATED.format(max_size=max_size))
