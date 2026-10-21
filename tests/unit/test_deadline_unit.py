"""utils/deadline.py 的單元測試：時間預算怎麼縮短請求、用完怎麼停，以及三條慢路徑都在預算內執行（不打外部網路）。"""

import threading
import time
from datetime import datetime

import pytest
from fastmcp.exceptions import ToolError

from tests.helpers import register_module_tools, scripted_server
from tools.taifex import intraday
from tools.tdcc import shareholding_distribution as tdcc
from utils import deadline, taifex
from utils.api_client import TWSEAPIClient
from utils.circuit_breaker import CircuitBreaker
from utils.deadline import request_timeout, time_budget
from utils.errors import DeadlineExceeded

pytestmark = pytest.mark.offline


class _Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


@pytest.fixture
def clock(monkeypatch):
    fake = _Clock()
    monkeypatch.setattr(deadline.time, "monotonic", fake)
    return fake


def test_no_budget_leaves_the_timeout_alone():
    assert request_timeout(30) == (30, False)


def test_budget_shortens_the_last_request_then_stops(clock):
    with time_budget(60, "可改指定日期"):
        assert request_timeout(30) == (30, False)
        clock.now += 45
        assert request_timeout(30) == (15, True)          # 只剩 15 秒：縮短，並標記是預算縮的
        clock.now += 15
        with pytest.raises(DeadlineExceeded, match=r"^超過 60 秒仍未完成（已送出 2 個請求）；可改指定日期$"):
            request_timeout(30)
    assert request_timeout(30) == (30, False)             # 離開區塊就沒有預算


def test_nested_budget_never_extends_the_outer_one(clock):
    with time_budget(10):
        clock.now += 8
        with time_budget(60):
            assert request_timeout(30) == (2, True)


def test_budget_belongs_to_its_own_thread(clock):
    seen = []
    with time_budget(1):
        clock.now += 5
        worker = threading.Thread(target=lambda: seen.append(request_timeout(30)))
        worker.start()
        worker.join()
    assert seen == [(30, False)], "另一個工具呼叫（另一條執行緒）不受這個預算影響"


def test_latest_day_walk_back_stops_at_its_budget(clock):
    calls = []

    def fetch(start, end):                                # 每一天都沒資料、每個請求要 25 秒
        request_timeout(30)
        calls.append(start)
        clock.now += 25
        return None

    with pytest.raises(DeadlineExceeded, match="超過 60 秒仍未完成（已送出 3 個請求）；可改指定日期"):
        taifex.fetch_period(fetch, "", "", 31)
    assert len(calls) == 3 < taifex.LATEST_LOOKBACK_DAYS


def test_a_period_query_has_no_walk_back_budget(clock):
    def fetch(start, end):
        assert deadline._current.get() is None
        return ["h"], [["r"]]

    assert taifex.fetch_period(fetch, "20261001", "20261002", 31)[0] == (["h"], [["r"]])


# ---------- 與 TWSEAPIClient 的整合（127.0.0.1） ----------

def test_slow_reply_past_the_budget_is_a_deadline_not_a_site_failure():
    with scripted_server((200, {}, b'{"late": true}', 2.0)) as (url, seen):
        client = TWSEAPIClient(request_interval=0, cache_ttl=0, breaker=CircuitBreaker(threshold=1))
        start = time.monotonic()
        with time_budget(0.3, "請稍後再試"):
            with pytest.raises(DeadlineExceeded, match="超過 0.3 秒仍未完成（已送出 1 個請求）"):
                client.fetch_json(url)
        assert time.monotonic() - start < 1.5, "要在預算到時就回來，不是等上游回完"
        assert client.fetch_json(url) == {"ok": True}, "預算用完不是網站的錯，circuit 不可因此打開"


def test_no_request_is_sent_once_the_budget_is_spent():
    with scripted_server() as (url, seen):
        client = TWSEAPIClient(request_interval=0, cache_ttl=0)
        with time_budget(0.01):
            time.sleep(0.05)
            with pytest.raises(DeadlineExceeded, match="已送出 0 個請求"):
                client.fetch_json(url)
        assert seen == []


# ---------- 三條慢路徑都在預算內執行 ----------

class _BudgetProbe:
    """記下每次請求當下的預算，然後中止工具（不需要真的回資料）。"""

    def __init__(self):
        self.budgets = []

    def fetch_bytes(self, url, **kwargs):
        budget = deadline._current.get()
        self.budgets.append(budget.seconds if budget else None)
        raise ConnectionError("probe")

    fetch_json = fetch_bytes


def test_intraday_runs_under_its_budget():
    probe = _BudgetProbe()
    fn = register_module_tools(intraday, probe)["get_futures_intraday"]
    with pytest.raises(ToolError, match="查詢失敗"):
        fn()
    assert probe.budgets == [intraday.INTRADAY_BUDGET]


def test_tdcc_trend_runs_under_its_budget_and_the_latest_week_does_not():
    probe = _BudgetProbe()
    fn = register_module_tools(tdcc, probe)["get_shareholding_distribution"]
    for weeks in (4, 1):
        with pytest.raises(ToolError, match="查詢失敗"):
            fn("2330", weeks=weeks)
    assert probe.budgets == [tdcc.TREND_BUDGET, None]


def test_budget_error_reaches_the_client_as_query_failed(monkeypatch):
    def spent(*args, **kwargs):
        raise DeadlineExceeded("超過 120 秒仍未完成（已送出 3 個請求）；已下載的交易日會快取，稍後再試會較快")

    client = TWSEAPIClient(request_interval=0, cache_ttl=0)
    monkeypatch.setattr(client, "fetch_bytes", spent)
    fn = register_module_tools(intraday, client)["get_futures_intraday"]
    with pytest.raises(ToolError, match=r"^查詢失敗: 超過 120 秒仍未完成"):
        fn()


def test_walk_back_label_is_unchanged_when_data_is_found(clock):
    today = taifex.taipei_today()
    parsed, label, error = taifex.fetch_period(lambda s, e: (["h"], [["r"]]), "", "", 31)
    assert (label, error) == (f"{today:%Y%m%d}（最新交易日）", None) and isinstance(today, datetime)
