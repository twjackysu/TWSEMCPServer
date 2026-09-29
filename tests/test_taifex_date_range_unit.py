"""parse_date_range 的單元測試（不打網路）。

期交所網站下載頁面（www.taifex.com.tw）的 9 個歷史查詢工具共用這段起訖日期驗證，
以往是各自複製一份。集中之後，這裡確保三種拒絕情形與邊界值不會在重構中被改掉。
"""

import pytest

from tools.taifex.futures_daily_history import parse_date_range


def test_valid_range_is_parsed():
    start_dt, end_dt, error = parse_date_range("20260601", "20260630", 31, "20260601")
    assert error is None
    assert (start_dt.year, start_dt.month, start_dt.day) == (2026, 6, 1)
    assert (end_dt.year, end_dt.month, end_dt.day) == (2026, 6, 30)


def test_same_day_range_is_allowed():
    _start_dt, _end_dt, error = parse_date_range("20260601", "20260601", 31, "20260601")
    assert error is None


@pytest.mark.parametrize("start_date,end_date", [
    ("2026/06/01", "20260630"),
    ("20260601", "2026-06-30"),
    ("20261301", "20261330"),
    ("", "20260630"),
])
def test_unparseable_dates_are_rejected(start_date, end_date):
    start_dt, end_dt, error = parse_date_range(start_date, end_date, 31, "20260601")
    assert (start_dt, end_dt) == (None, None)
    assert "日期格式錯誤" in error


def test_format_error_echoes_the_caller_s_example():
    """例示日期由呼叫端傳入，需與該工具 docstring 的範例一致."""
    _start_dt, _end_dt, error = parse_date_range("bad", "bad", 92, "20260401")
    assert "20260401" in error


def test_reversed_range_is_rejected():
    start_dt, end_dt, error = parse_date_range("20260630", "20260601", 31, "20260601")
    assert (start_dt, end_dt) == (None, None)
    assert "不可晚於結束日期" in error


def test_span_at_the_cap_is_allowed_but_one_day_over_is_not():
    """上限為閉區間：剛好 31 天可查，32 天要擋下並回報實際天數."""
    _start_dt, _end_dt, error = parse_date_range("20260601", "20260702", 31, "20260601")
    assert error is None

    start_dt, end_dt, error = parse_date_range("20260601", "20260703", 31, "20260601")
    assert (start_dt, end_dt) == (None, None)
    assert "31 天" in error and "收到 32 天" in error
