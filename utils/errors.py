"""Exceptions the data side raises for the tool layer to report.

utils/ cannot import fastmcp, so it cannot raise ToolError itself. ``toolkit.handle_api_errors``
turns ``InvalidArgument`` into ``ToolError`` with the message unchanged (no 查詢失敗 prefix): the
caller passed a bad argument, nothing failed upstream.
"""

import requests


class InvalidArgument(ValueError):
    """A tool argument the caller has to change; the message says how."""


class UpstreamFormatError(ValueError):
    """An upstream answered in a shape a gateway does not recognize (a field renamed or gone).

    Raised instead of guessing, so the tool reports 查詢失敗 rather than misreading columns or
    claiming there is no data. The daily contract tests should catch the same change.
    """


class DeadlineExceeded(TimeoutError):
    """A ``utils.deadline.time_budget`` ran out: the work stopped before its next request."""


class UpstreamUnavailable(requests.exceptions.ConnectionError):
    """A site's circuit is open (utils/circuit_breaker.py): the request was not sent.

    A ``ConnectionError`` because to every caller it is one — the upstream cannot be reached right
    now — and code that already treats connection failures as transient (the contract tests'
    ``*_or_skip`` helpers) handles it the same way.
    """
