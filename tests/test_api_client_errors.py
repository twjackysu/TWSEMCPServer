"""
測試上游故障不會被偽裝成「查無資料」。

fetch_company_data / fetch_latest_market_data 曾經把所有例外吞掉並回傳
None / []，導致 timeout、5xx、維護頁與「這家公司真的沒這筆資料」在工具輸出上
完全相同——@handle_api_errors 因此永遠不會觸發，MSG_QUERY_FAILED 形同死碼。
"""

import pytest
import requests

from utils.api_client import TWSEAPIClient
from utils.tool_factory import create_company_tool
from tests.helpers import _CapturingMCP

ENDPOINT = "/opendata/t187ap06_L_ci"


class _MaintenancePage:
    """200 OK，但 body 是 HTML 而非 JSON（TWSE 維護時的實際行為）."""

    status_code = 200
    text = "<html>系統維護中</html>"
    content = b"<html>"

    def raise_for_status(self):
        pass

    def json(self):
        raise ValueError("Expecting value: line 1 column 1 (char 0)")


def _raise(exc):
    def _fake(*args, **kwargs):
        raise exc

    return _fake


UPSTREAM_FAILURES = [
    pytest.param(_raise(requests.exceptions.Timeout("timed out")), id="timeout"),
    pytest.param(_raise(requests.exceptions.ConnectionError("refused")), id="connection-error"),
    pytest.param(_raise(requests.exceptions.HTTPError("503 Server Error")), id="http-503"),
    pytest.param(lambda *a, **kw: _MaintenancePage(), id="html-instead-of-json"),
]


@pytest.fixture
def client():
    # cache_ttl=0：確保每個測試都真的打一次（被 monkeypatch 攔下）而非讀到快取
    return TWSEAPIClient(cache_ttl=0)


@pytest.mark.parametrize("fake_request", UPSTREAM_FAILURES)
def test_fetch_company_data_propagates_failures(monkeypatch, client, fake_request):
    """故障必須往上拋，不能降級成 None（等同「查無此公司」）."""
    monkeypatch.setattr(requests, "request", fake_request)
    with pytest.raises(Exception):
        client.fetch_company_data(ENDPOINT, "2330")


@pytest.mark.parametrize("fake_request", UPSTREAM_FAILURES)
def test_fetch_latest_market_data_propagates_failures(monkeypatch, client, fake_request):
    """同上，不能降級成 []（等同「今天沒有行情」）."""
    monkeypatch.setattr(requests, "request", fake_request)
    with pytest.raises(Exception):
        client.fetch_latest_market_data("/exchangeReport/MI_INDEX")


@pytest.mark.parametrize("fake_request", UPSTREAM_FAILURES)
def test_tool_reports_failure_not_missing_data(monkeypatch, client, fake_request):
    """工具層輸出必須是「查詢失敗」，而非與查無資料無從分辨的空字串."""
    mcp = _CapturingMCP()
    create_company_tool(mcp, ENDPOINT, "probe_tool", "測試用", client)
    monkeypatch.setattr(requests, "request", fake_request)

    result = mcp.tools["probe_tool"]("2330")
    assert result.startswith("查詢失敗"), f"故障被偽裝成正常回應: {result!r}"


def test_missing_company_still_reads_as_missing(client):
    """對照組：真的查無此公司時，訊息要與「查詢失敗」明確區分."""
    mcp = _CapturingMCP()
    create_company_tool(mcp, ENDPOINT, "probe_tool", "測試用", client)

    result = mcp.tools["probe_tool"]("9999")
    assert result.startswith("查無"), f"預期「查無」訊息，實際: {result!r}"
    assert not result.startswith("查詢失敗")
