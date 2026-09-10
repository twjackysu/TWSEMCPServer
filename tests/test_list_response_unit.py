"""format_list_response 在「一筆都不剩」時的回覆（不打網路）。

清單工具幾乎都是先抓整份資料、再用 name 關鍵字或有效欄位條件過濾，最後交給
format_list_response 排版。過濾到一筆不剩是日常情況（關鍵字打錯、當天沒有符合的個股），
此時若回空字串，MCP 呼叫端看到的就是完全空白的工具回覆，跟工具壞掉無法區分。
"""

import pytest

from tests.helpers import register_module_tools
from utils.constants import MSG_NO_MATCHING_DATA
from utils.formatters import format_list_response
import tools.company.listing as listing
import tools.trading.market as market


class _StubClient:
    """只回固定資料的假 client，讓工具能離線跑完整條路徑."""

    def __init__(self, rows):
        self._rows = rows

    def fetch_data(self, endpoint, timeout=None):
        return list(self._rows)


def test_empty_list_says_why_instead_of_returning_blank():
    result = format_list_response([], "最近上市公司資料")
    assert result == MSG_NO_MATCHING_DATA.format(data_type="最近上市公司資料")


def test_non_empty_list_is_unchanged():
    result = format_list_response([{"Code": "2330"}], "測試資料")
    assert "共有 1 筆測試資料" in result
    assert "Code: 2330" in result


def test_name_filter_with_no_match_is_explicit():
    """create_list_tool 的 name 關鍵字過濾掉全部資料時要有訊息（涵蓋 27 支清單工具）."""
    client = _StubClient([{"Code": "2330", "Company": "台積電", "ListingDate": "1123456"}])
    tools = register_module_tools(listing, client)

    result = tools["get_recently_listed_companies"](name="不存在的公司")

    assert result.strip(), "過濾後無資料時回了空字串"
    assert "查無" in result, f"未說明查無符合條件的資料: {result!r}"


def test_direct_call_site_name_filter_with_no_match_is_explicit():
    """直接呼叫 format_list_response 的工具同樣不該回空字串."""
    client = _StubClient([
        {"Code": "2330", "Name": "台積電", "Number": "1", "NumberOfAnnouncement": "1",
         "TradingInfoForAttention": "-", "Date": "1123456", "ClosingPrice": "1000", "PE": "20"},
    ])
    tools = register_module_tools(market, client)

    result = tools["get_today_notice_stocks"](name="不存在的公司")

    assert result.strip(), "過濾後無資料時回了空字串"
    assert "查無" in result, f"未說明查無符合條件的資料: {result!r}"


@pytest.mark.parametrize("rows", [[], [{"Code": "", "Name": ""}]])
def test_source_with_no_usable_rows_still_reports_no_data(rows):
    """來源整份沒資料時仍走既有的 MSG_NO_DATA 路徑，不受本次修改影響."""
    tools = register_module_tools(market, _StubClient(rows))

    result = tools["get_today_notice_stocks"]()

    assert "目前沒有集中市場當日公布注意股票資料。" == result
