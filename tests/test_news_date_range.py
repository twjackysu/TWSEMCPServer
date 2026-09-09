"""get_twse_news 只給 start_date 時的月底推算（不打網路）。

只給 start_date 的分支要自行補出「該月最後一天」當作 end_date。原本的寫法是先把
start_date 換成民國年字串，再從換好的字串反推西元年份（"1130201" → 1130+1911=3041），
閏年判斷因此落在錯誤的年份上：查 2024-02 會以 28 日作結，2 月 29 日的新聞被靜默濾掉。
"""

import pytest

from tests.helpers import register_module_tools
from tools.company import news

NEWS_ROWS = [
    {"Date": "1130201", "Title": "二月第一天"},
    {"Date": "1130228", "Title": "二月倒數第二天"},
    {"Date": "1130229", "Title": "閏日"},
    {"Date": "1130301", "Title": "三月第一天"},
]


class _StubClient:
    """只回固定新聞清單的 client，取代 TWSEAPIClient 的 fetch_data."""

    def fetch_data(self, endpoint, timeout=None):
        return NEWS_ROWS


@pytest.fixture
def get_twse_news():
    return register_module_tools(news, _StubClient())["get_twse_news"]


def test_leap_day_is_included_when_only_start_date_given(get_twse_news):
    """2024-02 是閏月，2 月 29 日必須留在區間內."""
    result = get_twse_news(start_date="20240201")
    assert "1130229" in result, f"閏日被濾掉了: {result!r}"


def test_next_month_is_still_excluded(get_twse_news):
    """月底推算不能寬鬆到把下個月的新聞也帶進來."""
    result = get_twse_news(start_date="20240201")
    assert "1130301" not in result, f"區間超出當月: {result!r}"


def test_non_leap_february_ends_on_the_28th(get_twse_news):
    """對照組：2025-02 不是閏月，1130229 這種日期不該出現在結果中."""
    result = get_twse_news(start_date="20250201")
    assert result == "", f"預期查無 2025-02 的新聞，實際: {result!r}"
