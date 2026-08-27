"""
測試清單型工具的輸出上限。

這些工具原本把整份資料 join 成單一字串回傳，實測 get_warrant_basic_info 產出
37.85 MB、get_warrant_yearly_issuance_statistics 8.18M 字元、
get_options_daily_history 指定 contract_month 後仍有 2.65 MB——遠超任何模型的
context window。此處以「字元數天花板」為斷言，避免日後有人拿掉分頁。
"""

import pytest

from utils.api_client import TWSEAPIClient
from tests.helpers import register_module_tools
import tools.trading.warrants as warrants
import tools.history.margin_balance as margin_balance
import tools.history.bwibbu_all as bwibbu_all

# 寬鬆的上限：只要沒有分頁就會超出好幾個數量級，不必抓得太緊
MAX_CHARS = 100_000

TRADING_DATE = "20250102"


@pytest.fixture(scope="module")
def client():
    return TWSEAPIClient()


@pytest.mark.parametrize(
    "tool_name",
    [
        "get_warrant_basic_info",
        "get_warrant_daily_trading",
        "get_warrant_yearly_issuance_statistics",
    ],
)
def test_warrant_list_tools_are_bounded(client, tool_name):
    """權證三支清單工具不指定 code 時仍須分頁."""
    tools = register_module_tools(warrants, client)
    result = tools[tool_name]()
    assert len(result) < MAX_CHARS, f"{tool_name} 輸出 {len(result):,} 字元，未分頁"
    assert "共有" in result and "筆" in result, "應回報總筆數"


def test_warrant_pagination_advances(client):
    """offset 必須真的換頁."""
    tools = register_module_tools(warrants, client)
    first = tools["get_warrant_basic_info"](limit=5)
    second = tools["get_warrant_basic_info"](limit=5, offset=5)
    assert first != second, "offset 未生效，兩頁內容相同"


def test_margin_balance_is_bounded(client):
    tools = register_module_tools(margin_balance, client)
    result = tools["get_margin_balance"](TRADING_DATE)
    assert len(result) < MAX_CHARS, f"輸出 {len(result):,} 字元，未分頁"
    assert "offset=" in result, "未提示如何取得後續資料"


def test_margin_balance_offset_out_of_range_is_explicit(client):
    tools = register_module_tools(margin_balance, client)
    result = tools["get_margin_balance"](TRADING_DATE, offset=999_999)
    assert "超出範圍" in result, f"offset 越界未給明確訊息: {result[:120]!r}"


def test_market_valuation_is_bounded(client):
    tools = register_module_tools(bwibbu_all, client)
    result = tools["get_market_valuation_by_date"](TRADING_DATE)
    assert len(result) < MAX_CHARS, f"輸出 {len(result):,} 字元，未分頁"
    assert "offset=" in result, "未提示如何取得後續資料"


def test_market_valuation_offset_out_of_range_is_explicit(client):
    tools = register_module_tools(bwibbu_all, client)
    result = tools["get_market_valuation_by_date"](TRADING_DATE, offset=999_999)
    assert "超出範圍" in result, f"offset 越界未給明確訊息: {result[:120]!r}"
