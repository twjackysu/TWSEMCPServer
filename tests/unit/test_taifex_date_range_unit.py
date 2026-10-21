"""parse_date_range 的單元測試（不打網路）。

期交所網站下載頁面（www.taifex.com.tw）的 9 個歷史查詢工具共用這段起訖日期驗證，
以往是各自複製一份。日期格式在工具執行前由 toolkit.TradingDate 驗證（見 test_argument_validation_unit.py），
這裡只剩跨兩個日期的規則：起訖顛倒與區間上限，以及邊界值。
"""

import pytest

from utils.taifex import parse_date_range

pytestmark = pytest.mark.offline


def test_valid_range_is_parsed():
    start_dt, end_dt, error = parse_date_range("20260601", "20260630", 31)
    assert error is None
    assert (start_dt.year, start_dt.month, start_dt.day) == (2026, 6, 1)
    assert (end_dt.year, end_dt.month, end_dt.day) == (2026, 6, 30)


def test_same_day_range_is_allowed():
    _start_dt, _end_dt, error = parse_date_range("20260601", "20260601", 31)
    assert error is None


def test_reversed_range_is_rejected():
    start_dt, end_dt, error = parse_date_range("20260630", "20260601", 31)
    assert (start_dt, end_dt) == (None, None)
    assert "不可晚於結束日期" in error


def test_span_at_the_cap_is_allowed_but_one_day_over_is_not():
    """上限為閉區間：剛好 31 天可查，32 天要擋下並回報實際天數."""
    _start_dt, _end_dt, error = parse_date_range("20260601", "20260702", 31)
    assert error is None

    start_dt, end_dt, error = parse_date_range("20260601", "20260703", 31)
    assert (start_dt, end_dt) == (None, None)
    assert "31 天" in error and "收到 32 天" in error
