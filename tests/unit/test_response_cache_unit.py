"""TWSEAPIClient 的 fetch_json / fetch_bytes 回應快取（cache_ttl）單元測試（不打網路）。

快取只在工具明確傳 cache_ttl 時啟用（TDCC、國發會、央行、MOPS 這類大檔或易被限流的來源）。
這裡釘住：命中與過期、參數不同不共用、錯誤不快取、全域停用、容量上限、呼叫端改不到快取內容。
"""

import pytest
import requests

from utils.api_client import TWSEAPIClient

pytestmark = pytest.mark.offline


class _Resp:
    def __init__(self, content: bytes):
        self.content = content

    def json(self):
        raise AssertionError("有 cache_ttl 時應走 bytes 再 json.loads 的路徑")


class _CountingClient(TWSEAPIClient):
    def __init__(self, cache_ttl=60, bodies=None):
        super().__init__(request_interval=0, cache_ttl=cache_ttl)
        self.calls = []
        self.bodies = bodies or {}

    def _request(self, url, params=None, headers=None, timeout=None, method="GET", data=None, json_body=None):
        self.calls.append((method, url, params, data, json_body))
        body = self.bodies.get(url, b'{"rows": [1, 2]}')
        if isinstance(body, Exception):
            raise body
        return _Resp(body)


@pytest.fixture
def clock(monkeypatch):
    now = [1000.0]
    monkeypatch.setattr("utils.api_client.time.time", lambda: now[0])
    return now


def test_hit_within_ttl_and_refetch_after_expiry(clock):
    client = _CountingClient()
    client.fetch_json("https://x/a", params={"d": "1"}, cache_ttl=30)
    clock[0] += 29
    client.fetch_json("https://x/a", params={"d": "1"}, cache_ttl=30)
    assert len(client.calls) == 1
    clock[0] += 2
    client.fetch_json("https://x/a", params={"d": "1"}, cache_ttl=30)
    assert len(client.calls) == 2


def test_different_params_or_body_are_separate_entries(clock):
    client = _CountingClient()
    client.fetch_json("https://x/a", params={"d": "1"}, cache_ttl=30)
    client.fetch_json("https://x/a", params={"d": "2"}, cache_ttl=30)
    client.fetch_json("https://x/a", json_body={"year": "114"}, cache_ttl=30)
    client.fetch_json("https://x/a", json_body={"year": "115"}, cache_ttl=30)
    client.fetch_bytes("https://x/a", method="POST", data={"m": "09"}, cache_ttl=30)
    client.fetch_bytes("https://x/a", method="POST", data={"m": "10"}, cache_ttl=30)
    assert len(client.calls) == 6


def test_without_cache_ttl_every_call_hits_upstream(clock):
    client = _CountingClient()
    client.fetch_bytes("https://x/a")
    client.fetch_bytes("https://x/a")
    assert len(client.calls) == 2


def test_global_cache_off_disables_response_cache(clock):
    """TWSE_CACHE_TTL=0 要能關掉所有快取，包括工具自帶 cache_ttl 的呼叫."""
    client = _CountingClient(cache_ttl=0)
    client.fetch_bytes("https://x/a", cache_ttl=3600)
    client.fetch_bytes("https://x/a", cache_ttl=3600)
    assert len(client.calls) == 2


def test_failures_are_not_cached(clock):
    client = _CountingClient(bodies={"https://x/a": requests.ConnectionError("down")})
    with pytest.raises(requests.ConnectionError):
        client.fetch_bytes("https://x/a", cache_ttl=3600)
    client.bodies["https://x/a"] = b"ok"
    assert client.fetch_bytes("https://x/a", cache_ttl=3600) == b"ok"
    assert len(client.calls) == 2


def test_oldest_entry_is_evicted_at_capacity(clock):
    client = _CountingClient()
    client.response_cache_max_entries = 2
    for d in ("1", "2", "3"):
        client.fetch_json("https://x/a", params={"d": d}, cache_ttl=30)
    client.fetch_json("https://x/a", params={"d": "3"}, cache_ttl=30)  # 仍在快取
    client.fetch_json("https://x/a", params={"d": "1"}, cache_ttl=30)  # 已被淘汰
    assert len(client.calls) == 4
    assert len(client._response_cache) == 2


def test_callers_cannot_mutate_cached_data(clock):
    client = _CountingClient()
    first = client.fetch_json("https://x/a", cache_ttl=30)
    first["rows"].append(99)
    assert client.fetch_json("https://x/a", cache_ttl=30) == {"rows": [1, 2]}
