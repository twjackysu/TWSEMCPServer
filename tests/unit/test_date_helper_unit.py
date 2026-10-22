"""utils/date_helper.py 的西元 → 上游格式轉換（不打網路）。

工具一律收西元 YYYYMMDD（toolkit.TradingDate），送給上游前用這些函式轉成對方要的格式；每種格式都必須與
原本各工具自己寫的轉換逐字相同，否則送出的請求就變了。
"""

from datetime import date

import pytest

from utils.date_helper import roc_date, roc_day, roc_year_of, slash_date

pytestmark = pytest.mark.offline


@pytest.mark.parametrize("ymd,slashed,compact,year", [
    ("20260930", "115/09/30", "1150930", 115),
    ("20120502", "101/05/02", "1010502", 101),
    ("20101231", "99/12/31", "0991231", 99),  # 民國 100 年以前：緊湊格式補到 3 碼，斜線格式不補（與 MOPS 一致）
])
def test_roc_forms(ymd, slashed, compact, year):
    assert roc_date(ymd) == slashed
    assert roc_date(ymd, sep="") == compact
    assert roc_year_of(ymd) == year


def test_slash_date_for_tpex():
    assert slash_date("20260930") == "2026/09/30"


def test_roc_day_as_twse_monthly_reports_print_it():
    """FMTQIK / MI_5MINS_HIST 印的日期：民國 100 年以前前面補一個空白."""
    assert roc_day(date(2005, 1, 3)) == " 94/01/03"
    assert roc_day(date(2025, 1, 2)) == "114/01/02"
