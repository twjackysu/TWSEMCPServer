"""HTTP 傳輸層的單元測試：連線重用、cookie 不跨呼叫保留、retry 規則、TLS 設定（只打本機測試伺服器）。

retry 在 urllib3 的 connection pool 裡發生，monkeypatch 假 response 測不到，所以這裡用
127.0.0.1 上真的 HTTP 伺服器，照腳本一個一個回應。
"""

import ssl
import time

import pytest
import requests

from tests.helpers import scripted_server
from utils import http_transport
from utils.api_client import TWSEAPIClient

pytestmark = pytest.mark.offline


@pytest.fixture(autouse=True)
def fast_retries(monkeypatch):
    """真實的間隔是 1 秒起跳；測試把它縮短，但仍檢查「有等」."""
    monkeypatch.setattr(http_transport.UpstreamRetry, "MIN_BACKOFF", 0.05)
    monkeypatch.setattr(http_transport, "RETRY_BACKOFF_FACTOR", 0.05)
    monkeypatch.setattr(http_transport, "RETRY_JITTER", 0.0)


def _client():
    return TWSEAPIClient(request_interval=0, cache_ttl=0)


def test_gateway_error_is_retried_after_a_pause():
    with scripted_server((503, {}, b"busy")) as (url, seen):
        assert _client().fetch_json(url) == {"ok": True}
    assert len(seen) == 2
    assert seen[1]["at"] - seen[0]["at"] >= 0.05, "第一次重試也要等，不能立刻重打"


def test_post_query_forms_are_retried_too():
    with scripted_server((502, {}, b"")) as (url, seen):
        assert _client().fetch_bytes(url, method="POST", data={"q": "1"}) == b'{"ok": true}'
    assert [s["method"] for s in seen] == ["POST", "POST"]


def test_gives_up_after_two_retries_and_reports_the_failure():
    with scripted_server(*[(503, {}, b"busy")] * 5) as (url, seen):
        with pytest.raises(requests.HTTPError, match="503"):
            _client().fetch_json(url)
    assert len(seen) == 3


def test_short_retry_after_is_honoured():
    with scripted_server((429, {"Retry-After": "0"}, b"slow down")) as (url, seen):
        assert _client().fetch_json(url) == {"ok": True}
    assert len(seen) == 2


def test_long_retry_after_is_not_waited_out():
    """伺服器要我們等很久時直接放棄，不在網站鎖裡睡上好幾分鐘."""
    with scripted_server((429, {"Retry-After": "120"}, b"slow down")) as (url, seen):
        start = time.monotonic()
        with pytest.raises(requests.HTTPError, match="429"):
            _client().fetch_json(url)
    assert len(seen) == 1 and time.monotonic() - start < 5


def test_rate_limit_without_retry_after_and_client_errors_are_not_retried():
    for status in (429, 404):
        with scripted_server((status, {}, b"no")) as (url, seen):
            with pytest.raises(requests.HTTPError):
                _client().fetch_json(url)
        assert len(seen) == 1, status


def test_connections_are_reused_and_cookies_do_not_carry_over():
    with scripted_server((200, {"Set-Cookie": "sid=abc"}, b'{"ok": true}')) as (url, seen):
        client = _client()
        client.fetch_json(url)
        client.fetch_json(url)
    assert seen[0]["port"] == seen[1]["port"], "同一網站的請求應重用同一條連線"
    assert seen[1]["cookie"] is None, "前一次回應設的 cookie 不可帶到下一次呼叫"


def test_every_site_verifies_tls_and_cbc_skips_only_the_strict_flag():
    assert TWSEAPIClient().verify_ssl is True
    strict = http_transport.new_site_session("twse.com.tw").get_adapter("https://www.twse.com.tw/")
    assert "ssl_context" not in strict.poolmanager.connection_pool_kw  # requests' default context
    relaxed = http_transport.new_site_session("cbc.gov.tw").get_adapter("https://cpx.cbc.gov.tw/")
    context = relaxed.poolmanager.connection_pool_kw["ssl_context"]
    assert context.verify_mode == ssl.CERT_REQUIRED and context.check_hostname
    assert not context.verify_flags & ssl.VERIFY_X509_STRICT


def test_verification_off_uses_the_plain_adapter_everywhere():
    """TWSE_VERIFY_SSL=false：會檢查 hostname 的 context 不能搭配 CERT_NONE，央行也要用一般 adapter."""
    adapter = http_transport.new_site_session("cbc.gov.tw", verify=False).get_adapter("https://cpx.cbc.gov.tw/")
    assert "ssl_context" not in adapter.poolmanager.connection_pool_kw
