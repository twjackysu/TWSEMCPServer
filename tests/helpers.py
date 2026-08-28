"""Shared test helpers for e2e API tests."""

import json
import pytest
import requests
from utils.api_client import TWSEAPIClient

TAIFEX_OPENAPI_HOST = "openapi.taifex.com.tw"


def _is_taifex_csv_fallback(url: str, body: str) -> bool:
    """True when openapi.taifex.com.tw served an endpoint's CSV form instead of JSON.

    That host intermittently answers with the CSV rendering of the same dataset even
    when the request sends ``Accept: application/json``. Measured 2026-08-28: va01 and
    PutCallRatio served CSV for a stretch of minutes and JSON afterwards, while
    MarketDataOfMajorInstitutionalTradersDividedByFuturesAndOptionsBytheDate served CSV
    on 30 consecutive requests over 30s and its siblings served JSON throughout. The
    blocks are per-endpoint and last minutes, so ``--reruns 2 --reruns-delay 5`` does not
    clear them.

    It is the same data in another encoding, not a renamed or dropped field, so it is
    transient noise rather than the contract break these tests exist to catch.
    """
    if TAIFEX_OPENAPI_HOST not in url:
        return False
    stripped = body.lstrip("﻿").lstrip()
    if not stripped or stripped[0] in "{[":
        return False
    return "," in stripped.splitlines()[0]


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
        doc = getattr(e, "doc", None) or ""
        if not doc.strip():
            pytest.skip(f"Upstream returned an empty body: {url} — {e}")
        if _is_taifex_csv_fallback(url, doc):
            # Narrow exception to the rule above, scoped to one host. A site-wide,
            # permanent switch to CSV would still fail: see
            # test_taifex_api.py::test_openapi_still_serves_json_for_some_endpoint.
            pytest.skip(f"{TAIFEX_OPENAPI_HOST} served CSV instead of JSON (transient): {url}")
        raise
