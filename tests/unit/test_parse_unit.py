"""utils/parse.py：全專案共用的數字解析（不打網路）。

取代了 9 份各自實作的 _num / _float / _to_int / to_int / to_number，以及 3 處寫在程式裡的轉換。舊實作對
「沒有數字」的處理不一致（有的回 None、有的回 0）；現在一律回 None，要當 0 的地方由呼叫端寫明 ``or 0``。
"""

from decimal import Decimal

import pytest

from utils.parse import decimal_or_none, float_or_none, int_or_none

pytestmark = pytest.mark.offline

NO_NUMBER = ["", " ", "-", "--", "N/A", "n/a", None, "abc"]


@pytest.mark.parametrize("value,expected", [
    ("2,440.00", 2440.0), ("-1,234.5", -1234.5), ("+5.00", 5.0), (" 106.6400 ", 106.64), ("0", 0.0),
    ("14.5%", 14.5),                      # 百分比照印出來的數字讀
    (106.64, 106.64), (31855287, 31855287.0),  # MIS 有的投信送數字、有的送字串
    (Decimal("2480.00"), 2480.0), (Decimal("1234567.1234"), float(Decimal("1234567.1234"))),  # gateway 的 Decimal
])
def test_float_or_none_reads_numbers(value, expected):
    assert float_or_none(value) == expected


@pytest.mark.parametrize("value", NO_NUMBER)
def test_no_number_is_none_everywhere(value):
    assert float_or_none(value) is None
    assert int_or_none(value) is None
    assert decimal_or_none(value) is None


def test_int_or_none_wants_a_whole_number():
    assert int_or_none("31,855,287") == 31855287 and int_or_none("-68,513,664,272") == -68513664272
    assert int_or_none("1,000.00") is None  # 不是整數：交給 float_or_none / decimal_or_none
    assert (int_or_none("--") or 0) == 0     # 要當 0 時由呼叫端寫明


def test_decimal_keeps_the_printed_digits():
    assert str(decimal_or_none("2,440.00")) == "2440.00"
