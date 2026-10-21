"""get_company_profitability_analysis_summary 排序參數的單元測試（不打網路）。

docstring 列給呼叫端的是短欄名（毛利率(%)），程式卻只認 t187ap17_L 的完整欄名，
不符時默默改依公司代號排序——呼叫端拿到的排行完全不是它要的。
"""

import pytest
from fastmcp.exceptions import ToolError

from tests.helpers import register_module_tools
from tests.offline import OfflineClient
from tools.company import financials

pytestmark = pytest.mark.offline

GROSS = "毛利率(%)(營業毛利)/(營業收入)"
NET = "稅後純益率(%)(稅後純益)/(營業收入)"

ROWS = [
    {"公司代號": "1101", "公司名稱": "台泥", "年度": "115", "季別": "2", GROSS: "10.0", NET: "30.0"},
    {"公司代號": "2330", "公司名稱": "台積電", "年度": "115", "季別": "2", GROSS: "59.0", NET: "20.0"},
    {"公司代號": "2002", "公司名稱": "中鋼", "年度": "115", "季別": "2", GROSS: "5.0", NET: "1.0"},
]


@pytest.fixture
def tool():
    tools = register_module_tools(financials, OfflineClient({"/opendata/t187ap17_L": ROWS}))
    return tools["get_company_profitability_analysis_summary"]


def _codes(text: str) -> list:
    return [line.split()[1] for line in text.splitlines() if line.startswith("- ")]


@pytest.mark.parametrize("order_by", ["毛利率(%)", GROSS])
def test_documented_short_name_and_full_column_both_sort_by_that_column(tool, order_by):
    assert _codes(tool(order_by=order_by)) == ["2330", "1101", "2002"]


def test_default_is_net_margin_descending(tool):
    assert _codes(tool()) == ["1101", "2330", "2002"]


def test_unknown_sort_field_is_an_error_not_a_silent_fallback(tool):
    with pytest.raises(ToolError, match="order_by 必須是"):
        tool(order_by="本益比")
