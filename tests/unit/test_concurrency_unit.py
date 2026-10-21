"""工具並發執行與 TWSEAPIClient 執行緒安全的單元測試（不打網路）。

FastMCP 在 event loop 上直接呼叫同步函式，工具卡在 requests 或節流等待時整個 server
都會停住。@handle_api_errors 因此把工具本體丟到 worker thread，失敗時拋 ToolError
（MCP isError=true）。工具並發後，client 的節流與快取必須 thread-safe：
同一網站的請求仍一次一個、保持間隔；不同網站互不等待；相同請求只打一次上游。
"""

import asyncio
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import pytest
import requests
from fastmcp import Client, FastMCP

from utils.api_client import TWSEAPIClient, throttle_key
from utils.decorators import handle_api_errors

pytestmark = pytest.mark.offline


class _Resp:
    status_code = 200

    def __init__(self, content: bytes = b"[]"):
        self.content = content

    def raise_for_status(self):
        pass

    def json(self):
        return []


# ---------- @handle_api_errors on a real FastMCP server ----------

def _serve(mcp: FastMCP, calls):
    async def run():
        async with Client(mcp) as client:
            return await asyncio.gather(*(client.call_tool(name, args, raise_on_error=False) for name, args in calls))
    return asyncio.run(run())


def test_blocking_tools_run_concurrently():
    """三個同步工具要能同時執行：若在 event loop 上排隊，barrier 永遠湊不齊三方而逾時."""
    mcp = FastMCP("probe")
    barrier = threading.Barrier(3, timeout=5)

    @mcp.tool
    @handle_api_errors()
    def wait_for_peers() -> str:
        barrier.wait()
        return "ok"

    results = _serve(mcp, [("wait_for_peers", {})] * 3)
    assert [r.is_error for r in results] == [False] * 3
    assert [r.content[0].text for r in results] == ["ok"] * 3


def test_failure_is_an_mcp_error_not_a_normal_reply():
    mcp = FastMCP("probe")

    @mcp.tool
    @handle_api_errors()
    def broken(code: str) -> str:
        raise requests.exceptions.Timeout("timed out")

    (result,) = _serve(mcp, [("broken", {"code": "2330"})])
    assert result.is_error
    assert result.content[0].text.startswith("查詢失敗")


def test_tool_keeps_its_parameter_schema():
    """async wrapper 不能讓 FastMCP 看不到原函式的參數與 docstring."""
    mcp = FastMCP("probe")

    @mcp.tool
    @handle_api_errors()
    def documented(code: str, limit: int = 5) -> str:
        """說明文字。"""
        return code

    tool = asyncio.run(mcp.get_tools())["documented"]
    assert tool.description == "說明文字。"
    assert set(tool.parameters["properties"]) == {"code", "limit"}
    assert tool.parameters["required"] == ["code"]


# ---------- per-site throttle ----------

@pytest.mark.parametrize("url, site", [
    ("https://openapi.twse.com.tw/v1/opendata/t187ap03_L", "twse.com.tw"),
    ("https://www.twse.com.tw/rwd/zh/fund/T86", "twse.com.tw"),
    ("https://mops.twse.com.tw/mops/api/t05st01", "twse.com.tw"),
    ("https://mopsov.twse.com.tw/mops/web/ajax_t05st11", "twse.com.tw"),
    ("https://www.taifex.com.tw/cht/3/futDataDown", "taifex.com.tw"),
    ("https://openapi.taifex.com.tw/v1/SSFLists", "taifex.com.tw"),
    ("https://www.tpex.org.tw/openapi/v1/x", "tpex.org.tw"),
    ("https://tpex.org.tw/openapi/v1/x", "tpex.org.tw"),
])
def test_subdomains_of_one_exchange_share_a_throttle(url, site):
    assert throttle_key(url) == site


def test_same_site_requests_never_overlap(monkeypatch):
    """同一網站的請求即使來自多條執行緒也要一次一個，否則上游看到的是我方 IP 的瞬間連打."""
    active, peak, lock = [0], [0], threading.Lock()

    def fake_request(*args, **kwargs):
        with lock:
            active[0] += 1
            peak[0] = max(peak[0], active[0])
        time.sleep(0.02)
        with lock:
            active[0] -= 1
        return _Resp()

    monkeypatch.setattr(requests, "request", fake_request)
    client = TWSEAPIClient(request_interval=0, cache_ttl=0)
    urls = ["https://www.twse.com.tw/a", "https://openapi.twse.com.tw/v1/b", "https://mops.twse.com.tw/c"] * 2
    with ThreadPoolExecutor(max_workers=6) as pool:
        list(pool.map(client.fetch_bytes, urls))
    assert peak[0] == 1


def test_same_site_requests_stay_spaced_across_threads(monkeypatch):
    sent = []
    monkeypatch.setattr(requests, "request", lambda *a, **kw: sent.append(time.monotonic()) or _Resp())
    interval = 0.05
    client = TWSEAPIClient(request_interval=interval, cache_ttl=0)
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(client.fetch_bytes, ["https://www.twse.com.tw/x"] * 4))
    gaps = [b - a for a, b in zip(sorted(sent), sorted(sent)[1:])]
    assert min(gaps) >= interval * 0.95, f"同網站請求間隔不足: {gaps}"


def test_different_sites_do_not_wait_for_each_other(monkeypatch):
    """TAIFEX 慢下載進行中時，TWSE 請求不該排在它後面：兩邊同時在途 barrier 才湊得齊."""
    barrier = threading.Barrier(2, timeout=5)

    def fake_request(*args, **kwargs):
        barrier.wait()
        return _Resp()

    monkeypatch.setattr(requests, "request", fake_request)
    client = TWSEAPIClient(request_interval=0, cache_ttl=0)
    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(client.fetch_bytes, ["https://www.twse.com.tw/x", "https://www.taifex.com.tw/y"]))


# ---------- single-flight ----------

def _counting_request(calls, body: bytes):
    def fake_request(*args, **kwargs):
        with calls["lock"]:
            calls["n"] += 1
        time.sleep(0.05)
        return _Resp(body)
    return fake_request


def test_concurrent_identical_cached_requests_hit_upstream_once(monkeypatch):
    calls = {"n": 0, "lock": threading.Lock()}
    monkeypatch.setattr(requests, "request", _counting_request(calls, b'{"rows": [1]}'))
    client = TWSEAPIClient(request_interval=0, cache_ttl=60)
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda _: client.fetch_json("https://www.taifex.com.tw/x", cache_ttl=60), range(4)))
    assert calls["n"] == 1
    assert results == [{"rows": [1]}] * 4


def test_concurrent_reads_of_one_openapi_list_hit_upstream_once(monkeypatch):
    calls = {"n": 0, "lock": threading.Lock()}

    class _ListResp(_Resp):
        def json(self):
            return [{"公司代號": "2330"}]

    def fake_request(*args, **kwargs):
        with calls["lock"]:
            calls["n"] += 1
        time.sleep(0.05)
        return _ListResp()

    monkeypatch.setattr(requests, "request", fake_request)
    client = TWSEAPIClient(request_interval=0, cache_ttl=60)
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(lambda _: client.fetch_company_data("/opendata/t187ap03_L", "2330"), range(4)))
    assert calls["n"] == 1
