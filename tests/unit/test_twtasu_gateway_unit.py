"""sources/twse/twtasu.py 與 get_short_sale_lending_trades_history 的單元測試（不打網路）。

groups、fields 與資料列取自證交所真實回應（2025-01-03、2021-01-04）；上游真實格式由
tests/contract/test_history_tier2_api.py::TestShortLendingSalesGateway 驗證。
"""

import pytest

from sources.twse.twtasu import short_lending_sales
from tests.helpers import register_module_tools
from tests.offline import OfflineClient
from tools.history import short_sale_lending
from utils.errors import UpstreamFormatError

pytestmark = pytest.mark.offline

GROUPS = [{"start": 0, "span": 1, "title": ""}, {"start": 1, "span": 2, "title": "融券賣出成交"},
          {"start": 3, "span": 2, "title": "借券賣出成交"}]
FIELDS = ["證券名稱", "數量", "金額", "數量", "金額"]
ROWS = [["0050   元大台灣50      ", "11", "2,155,050", "0", "0"],
        ["2330   台積電          ", "0", "0", "522", "64,375,750"],
        ["合計", "21,933", "1,992,535,570", "175,773", "12,524,738,620"]]


def reply(rows=None, groups=None, date="20250103"):
    return {"stat": "OK", "date": date, "title": "114年01月03日當日融券賣出與借券賣出成交量值",
            "groups": GROUPS if groups is None else groups, "fields": FIELDS,
            "data": ROWS if rows is None else rows}


def _client(payload):
    return OfflineClient({"/afterTrading/TWTASU": payload})


def test_rows_become_typed_sales_without_the_total():
    day = short_lending_sales(_client(reply()), "20250103")
    etf, tsmc = day.sales
    assert (day.date, day.title) == ("20250103", "114年01月03日當日融券賣出與借券賣出成交量值")
    assert (etf.code, etf.name, etf.short_volume, etf.short_value, etf.lending_volume, etf.lending_value) == (
        "0050", "元大台灣50", 11, 2155050, 0, 0)
    assert (tsmc.code, tsmc.name, tsmc.lending_volume, tsmc.lending_value) == ("2330", "台積電", 522, 64375750)


def test_columns_are_found_by_group():
    swapped = [{"start": 0, "span": 1, "title": ""}, GROUPS[2], GROUPS[1]]
    rows = [[r[0], r[3], r[4], r[1], r[2]] for r in ROWS]
    assert short_lending_sales(_client(reply(rows, swapped)), "20250103") == short_lending_sales(_client(reply()), "20250103")


def test_no_data_and_changed_layout():
    assert short_lending_sales(_client({"stat": "查詢日期小於97年9月26日，請重新查詢!"}), "20050103") is None
    assert short_lending_sales(_client(reply([])), "20260927").sales == []
    with pytest.raises(UpstreamFormatError, match="groups 與 fields 對不上"):
        short_lending_sales(_client(reply(groups=GROUPS[:2])), "20250103")
    with pytest.raises(UpstreamFormatError, match="借券賣出成交/數量"):
        short_lending_sales(_client(reply(groups=GROUPS[:2] + [{"span": 2, "title": "借券賣出"}])), "20250103")
    with pytest.raises(UpstreamFormatError, match="4 欄"):
        short_lending_sales(_client(reply([ROWS[0][:4]])), "20250103")


def _tool(payload):
    return register_module_tools(short_sale_lending, _client(payload))["get_short_sale_lending_trades_history"]


def test_tool_prints_the_same_lines_as_before_the_gateway():
    text = _tool(reply())("20250103")
    assert text.startswith("【114年01月03日當日融券賣出與借券賣出成交量值】（共 2 筆）\n")
    assert "0050 元大台灣50 | 融券賣出: 量11 金額2,155,050 | 借券賣出: 量0 金額0" in text
    assert "2330 台積電 | 融券賣出: 量0 金額0 | 借券賣出: 量522 金額64,375,750" in text
    assert "合計" not in text


def test_tool_filters_and_reports_no_data():
    fn = _tool(reply())
    assert "共 1 筆" in fn("20250103", stock_no="2330") and "查無股票代號 合計" in fn("20250103", stock_no="合計")
    assert "查無名稱包含「鴻海」" in fn("20250103", name="鴻海")
    assert _tool(reply([]))("20260927") == "查無 20260927 的融券借券賣出成交量值資料"
    assert "請確認該日期為交易日" in _tool({"stat": "很抱歉，沒有符合條件的資料!"})("20260927")
