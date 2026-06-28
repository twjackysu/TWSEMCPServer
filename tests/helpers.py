"""Shared test helpers for e2e API tests."""

import pytest
import requests
from utils.api_client import TWSEAPIClient


def fetch_or_skip(url: str, **kwargs):
    """Fetch URL; skip test on upstream 5xx or connection error. 404 still FAILs."""
    try:
        return TWSEAPIClient.get_json(url, **kwargs)
    except requests.HTTPError as e:
        if e.response is not None and e.response.status_code >= 500:
            pytest.skip(f"Upstream server error ({e.response.status_code}): {url}")
        raise
    except requests.ConnectionError as e:
        pytest.skip(f"Cannot reach upstream: {url} — {e}")
