"""Shared test helpers for e2e API tests."""

import json
import pytest
import requests
from utils.api_client import TWSEAPIClient


def fetch_or_skip(url: str, **kwargs):
    """Fetch URL; skip test on upstream 5xx, empty body, or connection error. 404 still FAILs.

    A response body that parses to valid-but-wrong JSON (renamed/missing/reordered fields)
    is NOT skipped here — it's returned as-is so the caller's own field assertions run and
    fail normally. Only genuinely transient conditions are skipped.
    """
    try:
        return TWSEAPIClient.get_instance().fetch_json(url, **kwargs)
    except requests.HTTPError as e:
        if e.response is not None and e.response.status_code >= 500:
            pytest.skip(f"Upstream server error ({e.response.status_code}): {url}")
        raise
    except requests.ConnectionError as e:
        pytest.skip(f"Cannot reach upstream: {url} — {e}")
    except requests.exceptions.ChunkedEncodingError as e:
        # Response stream cut off mid-transfer — a network-level failure, not a schema
        # change, so always transient.
        pytest.skip(f"Upstream connection dropped mid-response: {url} — {e}")
    except json.JSONDecodeError as e:
        # Only skip on a genuinely empty body (upstream hiccup). A non-empty body that
        # fails to parse (e.g. the endpoint started returning CSV/HTML instead of JSON —
        # see issue #58 for a real occurrence) is a permanent format change, not a
        # transient failure, so let it raise and fail the test instead of masking it.
        if not (getattr(e, "doc", None) or "").strip():
            pytest.skip(f"Upstream returned an empty body: {url} — {e}")
        raise


class _CapturingMCP:
    """Minimal stand-in for FastMCP that records the functions modules register.

    ``register_tools`` only ever needs ``.tool`` — either bare (``@mcp.tool``) or
    called with keywords (``mcp.tool(name=..., description=...)``). Capturing the
    undecorated callables lets tests exercise a tool end-to-end without spinning
    up a server.
    """

    def __init__(self):
        self.tools = {}

    def tool(self, *args, **kwargs):
        if args and callable(args[0]):
            fn = args[0]
            self.tools[fn.__name__] = fn
            return fn

        name = kwargs.get("name")

        def decorator(fn):
            self.tools[name or fn.__name__] = fn
            return fn

        return decorator


def register_module_tools(module, client=None):
    """Register ``module``'s tools against a capturing MCP and return {name: fn}."""
    mcp = _CapturingMCP()
    module.register_tools(mcp, client or TWSEAPIClient.get_instance())
    return mcp.tools
