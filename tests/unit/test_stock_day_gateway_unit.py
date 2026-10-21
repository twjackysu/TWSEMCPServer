"""sources/twse/stock_day.py 與 get_stock_history 的單元測試（不打網路）。

上游真實格式由 tests/contract/test_history_api.py::TestStockDayGateway 驗證。
"""

from datetime import date
from decimal import Decimal

import pytest

from sources.twse.stock_day import stock_day_month
from tests.helpers import register_module_tools
from tests.offline import OfflineClient
from tools.history import stock_day as stock_day_tool
from utils.errors import UpstreamFormatError

pytestmark = pytest.mark.offline

FIELDS = ["日期", "成交股數", "成交金額", "開盤價", "最高價", "最低價", "收盤價", "漲跌價差", "成交筆數", "註記"]
ROWS = [
    ["115/09/01", "31,855,287", "77,463,413,685", "2,395.00", "2,440.00", "2,390.00", "2,440.00", "+35.00", "65,271", ""],
    ["115/09/02", "0", "0", "--", "--", "--", "--", " 0.00", "0", ""],
]
REPLY = {"stat": "OK", "title": "115年09月 2330 台積電           各日成交資訊", "fields": FIELDS, "data": ROWS}


def _month(reply, code="2330"):
    return stock_day_month(OfflineClient({"/exchangeReport/STOCK_DAY": reply}), code, 2026, 9)


def test_rows_become_typed_values_with_their_printed_digits():
    month = _month(REPLY)
    assert (month.code, month.name) == ("2330", "台積電")
    first, untraded = month.rows
    assert first.day == date(2026, 9, 1)
    assert (first.volume, first.value, first.transactions) == (31855287, 77463413685, 65271)
    assert first.close == Decimal("2440.00") and str(first.close) == "2440.00"
    assert first.change == "+35.00"
    assert (untraded.open, untraded.close) == (None, None) and untraded.change == " 0.00"


def test_columns_are_found_by_name_not_position():
    order = [9, 8, 7, 6, 5, 4, 3, 2, 1, 0]
    reply = {**REPLY, "fields": [FIELDS[i] for i in order], "data": [[r[i] for i in order] for r in ROWS]}
    assert _month(reply).rows == _month(REPLY).rows


def test_renamed_column_is_an_error_not_a_misread():
    reply = {**REPLY, "fields": ["日期", "成交量"] + FIELDS[2:]}
    with pytest.raises(UpstreamFormatError, match="成交股數"):
        _month(reply)


def test_changed_date_format_is_an_error():
    reply = {**REPLY, "data": [["2026-09-01"] + ROWS[0][1:]]}
    with pytest.raises(UpstreamFormatError, match="日期格式"):
        _month(reply)


def test_no_data_is_none():
    assert _month({"stat": "很抱歉，沒有符合條件的資料!", "total": 0}) is None
    assert _month({**REPLY, "data": []}) is None


def test_requests_the_first_of_the_month():
    seen = {}

    def route(params, _body):
        seen.update(params)
        return REPLY

    stock_day_month(OfflineClient({"/exchangeReport/STOCK_DAY": route}), "2330", 2026, 9)
    assert seen == {"response": "json", "stockNo": "2330", "date": "20260901"}


def _tool(reply=REPLY):
    return register_module_tools(stock_day_tool, OfflineClient({"/exchangeReport/STOCK_DAY": reply}))["get_stock_history"]


def test_tool_prints_the_same_line_as_before_the_gateway():
    text = _tool()("2330", "20260915")
    assert text.splitlines()[0] == "【115年09月 2330 台積電           各日成交資訊】"
    assert ("日期: 2026-09-01 | 開: 2395.00 | 高: 2440.00 | 低: 2390.00 | 收: 2440.00 | 漲跌: +35.00 | "
            "成交量: 31855287 | 成交金額: 77463413685 | 筆數: 65271") in text
    assert "日期: 2026-09-02 | 開: -- | 高: -- | 低: -- | 收: -- | 漲跌:  0.00 | 成交量: 0 | 成交金額: 0 | 筆數: 0" in text


