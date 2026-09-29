"""tests/helpers.py 判斷式的單元測試（不打網路）。

_is_taifex_csv_fallback 與 records_or_skip 決定「該 skip 還是該讓測試紅」，判錯任一邊
都有代價：太寬鬆會把真正的 schema 破壞藏起來，太嚴格則 CI 會因上游暫時性狀況
（openapi.taifex.com.tw 的 CSV 區間、連假後的空資料）隨機變紅。
"""

import pytest

from tests.helpers import _is_taifex_csv_fallback, records_or_skip

pytestmark = pytest.mark.offline

TAIFEX_URL = "https://openapi.taifex.com.tw/v1/PutCallRatio"
TWSE_URL = "https://openapi.twse.com.tw/v1/opendata/t187ap03_L"

CSV_BODY = "日期,賣權成交量,買權成交量\n20260827,158174,129911\n"


@pytest.mark.parametrize("body", [CSV_BODY, "﻿" + CSV_BODY])
def test_detects_taifex_csv_with_and_without_bom(body):
    assert _is_taifex_csv_fallback(TAIFEX_URL, body)


def test_other_hosts_are_never_excused():
    """TWSE 回 CSV 是真的格式變更（issue #58），不得比照辦理."""
    assert not _is_taifex_csv_fallback(TWSE_URL, CSV_BODY)


@pytest.mark.parametrize("body", ['[{"Date": "20260827"}]', '{"stat": "OK"}', "  "])
def test_json_or_empty_bodies_are_not_csv(body):
    assert not _is_taifex_csv_fallback(TAIFEX_URL, body)


def test_html_maintenance_page_is_not_excused():
    """HTML 錯誤頁沒有逗號分隔的表頭，不該被當成 CSV 而放行."""
    assert not _is_taifex_csv_fallback(TAIFEX_URL, "<html><body>維護中</body></html>")


def test_records_or_skip_returns_records():
    data = [{"Date": "20260929"}]
    assert records_or_skip(data, "probe") is data


def test_records_or_skip_skips_empty_list():
    """上游今天沒資料（如連假後的 t187ap42_L）不是 interface 變更，應 skip."""
    with pytest.raises(pytest.skip.Exception):
        records_or_skip([], "probe")


@pytest.mark.parametrize("data", [{"stat": "OK"}, None, "日期,成交量"])
def test_records_or_skip_fails_when_not_a_list(data):
    """回傳型別變了才是 interface 變更，必須 fail 而非 skip."""
    with pytest.raises(AssertionError):
        records_or_skip(data, "probe")
