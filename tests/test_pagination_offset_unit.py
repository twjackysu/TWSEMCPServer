"""自行分頁的工具在 offset 翻過資料尾端時的回覆（不打網路）。

format_list_response 已經會在 offset 越界時回 MSG_OFFSET_OUT_OF_RANGE（見
test_list_response_unit.py），但有 14 支工具不經過它、自己切 page_data 並自己組表頭。
那些工具原本會輸出「共 2 筆…顯示第 1000–2 筆」這種不可能的區間後面接零列資料，
呼叫端無從分辨是自己翻過頭還是工具壞掉。此處逐一釘住這個行為。
"""

import pytest

from tests.helpers import register_module_tools
import tools.company.basic_info as basic_info
import tools.history.all_stocks_daily_close as all_stocks_daily_close
import tools.history.block_trades_detail as block_trades_detail
import tools.history.foreign_holdings_history as foreign_holdings_history
import tools.history.institutional as institutional
import tools.history.short_sale_lending as short_sale_lending
import tools.market.statistics as statistics
import tools.otc.daily_close as otc_daily_close
import tools.otc.index as otc_index
import tools.otc.institutional as otc_institutional
import tools.otc.margin_balance as otc_margin_balance
import tools.otc.odd_lot as otc_odd_lot
import tools.otc.peratio as otc_peratio
import tools.trading.market as market

TRADING_DATE = "20250102"


class _StubClient:
    """只回固定 payload 的假 client，讓工具離線跑完整條路徑."""

    def __init__(self, payload):
        self._payload = payload

    def fetch_json(self, url, params=None, timeout=None, headers=None):
        return self._payload

    def fetch_data(self, endpoint, timeout=None):
        return self._payload


def _legacy(rows):
    """TWSE legacy JSON 端點的回傳形狀."""
    return {"stat": "OK", "data": rows}


# 每支工具的最小可用 payload：欄位數要足夠讓 in-range 的那一頁也能正常排版。
DAILY_CLOSE_ROW = ["2330", "台積電"] + ["1"] * 14                      # 16 欄，tuple 解包
SHORT_SALE_BALANCE_ROW = ["2330", "台積電"] + ["0"] * 13                # 融券 6 + 借券 6 + 備註
SHORT_SALE_TRADES_ROW = ["2330   台積電", "0", "0", "0", "0"]
BLOCK_TRADE_ROW = ["2330", "台積電", "鉅額中盤", "1000", "10", "10000"]  # 6 欄，tuple 解包
FOREIGN_HOLDINGS_ROW = ["2330", "台積電", "TW0002330008", "100", "10", "90", "10.00", "90.00"]
T86_ROW = ["2330", "台積電"] + ["0"] * 16 + ["1,000"]                   # row[18] 非 0 才算有法人進出

CASES = [
    (
        all_stocks_daily_close,
        "get_all_stocks_daily_close",
        {"date": TRADING_DATE},
        {"stat": "OK", "tables": [{"title": f"{TRADING_DATE} 每日收盤行情", "data": [DAILY_CLOSE_ROW]}]},
    ),
    (
        short_sale_lending,
        "get_short_sale_lending_balance_history",
        {"date": TRADING_DATE},
        _legacy([SHORT_SALE_BALANCE_ROW]),
    ),
    (
        short_sale_lending,
        "get_short_sale_lending_trades_history",
        {"date": TRADING_DATE},
        _legacy([SHORT_SALE_TRADES_ROW]),
    ),
    (
        block_trades_detail,
        "get_block_trades_detail",
        {"date": TRADING_DATE},
        _legacy([BLOCK_TRADE_ROW]),
    ),
    (
        foreign_holdings_history,
        "get_foreign_holdings_history",
        {"date": TRADING_DATE},
        _legacy([FOREIGN_HOLDINGS_ROW]),
    ),
    (
        institutional,
        "get_twse_institutional_investors_summary",
        {"date": TRADING_DATE},
        _legacy([T86_ROW]),
    ),
    (
        statistics,
        "get_margin_trading_info",
        {},
        [{"Item": "融資", "TodayBalance": "100"}],
    ),
    (
        basic_info,
        "get_companies_with_independent_directors",
        {},
        [{"公司代號": "2330", "公司名稱": "台積電"}],
    ),
    (
        market,
        "get_top_20_volume_stocks",
        {},
        [{"Rank": "1", "Code": "2330", "Name": "台積電", "Date": TRADING_DATE}],
    ),
    (
        market,
        "get_daily_securities_lending_volume",
        {},
        [
            {"TWSECode": "2330", "TWSEAvailableVolume": "100"},
            {"GRETAICode": "6488", "GRETAIAvailableVolume": "100"},
        ],
    ),
    (
        otc_daily_close,
        "get_otc_daily",
        {},
        [{"SecuritiesCompanyCode": "6488", "CompanyName": "環球晶"}],
    ),
    (
        otc_margin_balance,
        "get_otc_margin_balance",
        {},
        [{"SecuritiesCompanyCode": "6488", "CompanyName": "環球晶"}],
    ),
    (
        otc_odd_lot,
        "get_otc_odd_lot",
        {},
        [{"SecuritiesCompanyCode": "6488", "CompanyName": "環球晶"}],
    ),
    (
        otc_peratio,
        "get_otc_valuation",
        {},
        [{"SecuritiesCompanyCode": "6488", "CompanyName": "環球晶"}],
    ),
    (
        otc_institutional,
        "get_otc_institutional",
        {},
        [{"SecuritiesCompanyCode": "6488", "CompanyName": "環球晶"}],
    ),
    (
        otc_index,
        "get_otc_index",
        {},
        [{"Date": TRADING_DATE, "Close": "250"}],
    ),
]

CASE_IDS = [f"{module.__name__}::{tool_name}" for module, tool_name, _kwargs, _payload in CASES]


@pytest.mark.parametrize("module,tool_name,kwargs,payload", CASES, ids=CASE_IDS)
def test_offset_past_the_last_record_is_explicit(module, tool_name, kwargs, payload):
    """offset 翻過尾端時要講清楚，不能只回一個空頁的表頭."""
    tools = register_module_tools(module, _StubClient(payload))

    result = tools[tool_name](offset=999, **kwargs)

    assert "超出範圍" in result, f"offset 越界未給明確訊息: {result!r}"
    assert "顯示第 1000" not in result, f"仍印出不可能的分頁區間: {result!r}"


@pytest.mark.parametrize("module,tool_name,kwargs,payload", CASES, ids=CASE_IDS)
def test_first_page_is_unchanged(module, tool_name, kwargs, payload):
    """對照組：offset 還在範圍內時輸出不受影響（確認上面的守衛不會誤判）."""
    tools = register_module_tools(module, _StubClient(payload))

    result = tools[tool_name](**kwargs)

    assert "超出範圍" not in result, f"offset=0 被誤判為越界: {result!r}"
    assert "查詢失敗" not in result, f"工具拋出例外: {result!r}"
    assert "共" in result, f"未輸出總筆數表頭: {result!r}"


def test_securities_lending_prints_only_the_market_that_still_has_rows():
    """兩市場共用 offset：只有一邊翻過尾端時，該區塊要整段不印，而非印出空區塊."""
    payload = [
        {"TWSECode": "2330", "TWSEAvailableVolume": "100"},
        {"TWSECode": "2317", "TWSEAvailableVolume": "200"},
        {"GRETAICode": "6488", "GRETAIAvailableVolume": "300"},
    ]
    tools = register_module_tools(market, _StubClient(payload))

    result = tools["get_daily_securities_lending_volume"](limit=1, offset=1)

    assert "【上市股票】" in result, "上市還有第 2 筆，卻沒印出來"
    assert "【上櫃股票】" not in result, "上櫃只有 1 筆，offset=1 已越界卻仍印出區塊"


def test_no_match_after_name_filter_is_explicit():
    """name 關鍵字過濾到一筆不剩時要有訊息，不能回「共有 0 筆」的空表頭."""
    payload = [{"Rank": "1", "Code": "2330", "Name": "台積電", "Date": TRADING_DATE}]
    tools = register_module_tools(market, _StubClient(payload))

    result = tools["get_top_20_volume_stocks"](name="不存在的公司")

    assert "查無" in result, f"未說明查無符合條件的資料: {result!r}"
    assert "共有 0 筆" not in result, f"仍輸出 0 筆的空表頭: {result!r}"
