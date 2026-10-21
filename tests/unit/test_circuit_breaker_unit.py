"""utils/circuit_breaker.py 的單元測試：哪些回應算失敗、何時冷卻、冷卻後怎麼恢復（不打外部網路）。

狀態機用假時鐘測；與 TWSEAPIClient 的整合用 127.0.0.1 上的 scripted_server。
"""

import pytest
import requests

from tests.helpers import scripted_server
from utils.api_client import TWSEAPIClient
from utils.circuit_breaker import CircuitBreaker, Failure, failure_of_exception, failure_of_response
from utils.errors import UpstreamUnavailable

pytestmark = pytest.mark.offline


# ---------- 什麼算失敗 ----------

@pytest.mark.parametrize("status,body,expect_json,expected", [
    (200, b'{"stat": "OK"}', True, None),
    (200, b"\xef\xbb\xbf[]", True, None),
    (404, b"not found", True, None),                       # 我們的請求錯了，網站是好的
    (400, b"", True, None),
    (200, "日期,契約,價格\n2026/10/21,TX,1".encode("utf-8"), True, None),  # TAIFEX openapi 的 CSV 形式：只是格式退化
    (200, b"<html>report</html>", False, None),            # 不期待 JSON 的 HTML 頁面（MOPS 舊頁、SITCA…）是正常的
    (200, b"", True, Failure("空白回應")),
    (200, b"  <!DOCTYPE html><html>maintenance</html>", True, Failure("回應是 HTML 頁面而非 JSON（可能被擋或維護中）")),
    (503, b"busy", False, Failure("HTTP 503")),
    (403, b"", False, Failure("HTTP 403", blocked=True)),
    (429, b"", False, Failure("HTTP 429", blocked=True)),
    (200, b"<html>FOR SECURITY REASONS, THIS PAGE CAN NOT BE ACCESSED!</html>", False,
     Failure("被來源的防爬機制擋下", blocked=True)),
])
def test_response_classification(status, body, expect_json, expected):
    assert failure_of_response(status, body, expect_json) == expected


def test_retry_after_is_kept_as_a_hint():
    assert failure_of_response(429, b"", False, {"Retry-After": "120"}).retry_after == 120
    assert failure_of_response(503, b"", False, {"Retry-After": "Wed, 21 Oct 2026 07:28:00 GMT"}).retry_after == 0


@pytest.mark.parametrize("exc,expected", [
    (requests.exceptions.ReadTimeout("slow"), "逾時"),
    (requests.exceptions.ConnectionError("refused"), "連線失敗（ConnectionError）"),
    (requests.exceptions.ChunkedEncodingError("cut"), "連線失敗（ChunkedEncodingError）"),
    (requests.exceptions.HTTPError("503"), None),           # 沒有 response：說不出網站狀態
    (requests.exceptions.InvalidURL("bad"), None),
])
def test_exception_classification(exc, expected):
    failure = failure_of_exception(exc)
    assert (failure.reason if failure else None) == expected


# ---------- 狀態機 ----------

class _Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


def _breaker(**kw):
    clock = _Clock()
    return CircuitBreaker(threshold=3, cooldown=30, max_cooldown=600, clock=clock, **kw), clock


def test_opens_after_threshold_failures_in_a_row():
    breaker, _ = _breaker()
    breaker.failure("twse.com.tw", Failure("逾時"))
    breaker.failure("twse.com.tw", Failure("逾時"))
    breaker.check("twse.com.tw")  # 兩次還不擋
    breaker.failure("twse.com.tw", Failure("HTTP 503"))
    with pytest.raises(UpstreamUnavailable, match="twse.com.tw 暫停查詢中，約 30 秒後恢復（連續 3 次失敗，最後一次：HTTP 503）"):
        breaker.check("twse.com.tw")


def test_a_success_resets_the_count():
    breaker, _ = _breaker()
    for _ in range(2):
        breaker.failure("twse.com.tw", Failure("逾時"))
    breaker.success("twse.com.tw")
    for _ in range(2):
        breaker.failure("twse.com.tw", Failure("逾時"))
    breaker.check("twse.com.tw")


def test_a_refusal_opens_at_once_and_honours_a_longer_retry_after():
    breaker, _ = _breaker()
    breaker.failure("twse.com.tw", Failure("HTTP 429", blocked=True, retry_after=120))
    with pytest.raises(UpstreamUnavailable, match="約 120 秒"):
        breaker.check("twse.com.tw")


def test_sites_are_independent():
    breaker, _ = _breaker()
    breaker.failure("twse.com.tw", Failure("HTTP 403", blocked=True))
    breaker.check("tpex.org.tw")
    with pytest.raises(UpstreamUnavailable):
        breaker.check("twse.com.tw")


def test_probe_after_cooldown_reopens_with_doubled_cooldown_or_closes():
    breaker, clock = _breaker()
    breaker.failure("twse.com.tw", Failure("HTTP 403", blocked=True))
    clock.now += 30
    breaker.check("twse.com.tw")                      # 冷卻結束：放一個請求過去試
    breaker.failure("twse.com.tw", Failure("逾時"))   # 試探失敗：不必再等滿 3 次就重新冷卻
    with pytest.raises(UpstreamUnavailable, match="約 60 秒"):
        breaker.check("twse.com.tw")
    clock.now += 60
    breaker.success("twse.com.tw")                    # 試探成功：恢復，冷卻時間也歸零
    breaker.failure("twse.com.tw", Failure("HTTP 403", blocked=True))
    with pytest.raises(UpstreamUnavailable, match="約 30 秒"):
        breaker.check("twse.com.tw")


def test_cooldown_is_capped():
    breaker, clock = _breaker()
    for _ in range(10):
        breaker.failure("twse.com.tw", Failure("HTTP 403", blocked=True))
        clock.now += 10_000
    breaker.failure("twse.com.tw", Failure("HTTP 403", blocked=True, retry_after=86_400))
    with pytest.raises(UpstreamUnavailable, match="約 600 秒"):
        breaker.check("twse.com.tw")


def test_threshold_zero_disables_it():
    breaker = CircuitBreaker(threshold=0)
    for _ in range(5):
        breaker.failure("twse.com.tw", Failure("HTTP 403", blocked=True))
    breaker.check("twse.com.tw")


def test_unavailable_is_a_connection_error():
    """契約測試的 *_or_skip 與其他把連線失敗當暫時性的程式，會一視同仁地處理它."""
    assert issubclass(UpstreamUnavailable, requests.exceptions.ConnectionError)


# ---------- 與 TWSEAPIClient 的整合 ----------

def _client(**kw):
    return TWSEAPIClient(request_interval=0, cache_ttl=60, breaker=CircuitBreaker(threshold=3, cooldown=30, **kw))


def test_client_stops_sending_after_three_html_replies_but_still_serves_its_cache():
    html = (200, {}, b"<html>busy</html>")
    with scripted_server((200, {}, b'{"ok": true}'), html, html, html) as (url, seen):
        client = _client()
        assert client.fetch_json(url, params={"q": "cached"}, cache_ttl=60) == {"ok": True}
        for _ in range(3):
            with pytest.raises(ValueError):           # JSON 解析失敗照舊往上拋
                client.fetch_json(url)
        with pytest.raises(UpstreamUnavailable, match="回應是 HTML 頁面"):
            client.fetch_json(url)
        assert len(seen) == 4, "冷卻期間不能再送出請求"
        assert client.fetch_json(url, params={"q": "cached"}, cache_ttl=60) == {"ok": True}, "快取照常可用"
        assert len(seen) == 4


def test_client_opens_at_once_on_a_rate_limit():
    with scripted_server((429, {}, b"slow down")) as (url, seen):
        client = _client()
        with pytest.raises(requests.HTTPError, match="429"):
            client.fetch_bytes(url)
        with pytest.raises(UpstreamUnavailable, match="HTTP 429"):
            client.fetch_bytes(url)
        assert len(seen) == 1


def test_html_pages_fetched_as_bytes_do_not_count():
    page = (200, {}, b"<html>MOPS legacy table</html>")
    with scripted_server(page, page, page, page) as (url, seen):
        client = _client()
        for _ in range(4):
            assert client.fetch_bytes(url).startswith(b"<html>")
        assert len(seen) == 4
