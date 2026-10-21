"""Exceptions the data side raises for the tool layer to report.

utils/ cannot import fastmcp, so it cannot raise ToolError itself. ``toolkit.handle_api_errors``
turns ``InvalidArgument`` into ``ToolError`` with the message unchanged (no 查詢失敗 prefix): the
caller passed a bad argument, nothing failed upstream.
"""


class InvalidArgument(ValueError):
    """A tool argument the caller has to change; the message says how."""


class UpstreamFormatError(ValueError):
    """An upstream answered in a shape a gateway does not recognize (a field renamed or gone).

    Raised instead of guessing, so the tool reports 查詢失敗 rather than misreading columns or
    claiming there is no data. The daily contract tests should catch the same change.
    """
