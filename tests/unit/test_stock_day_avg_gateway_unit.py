"""sources/twse/stock_day_avg.py 與 get_stock_monthly_average 的單元測試（不打網路）。

資料列取自證交所真實回應（2330 的 2005-01 與 2025-01）；上游真實格式由
tests/contract/test_history_api.py::TestStockMonthlyAverageGateway 驗證。
"""

from datetime import date
from decimal import Decimal

import pytest

from sources.twse.stock_day_avg import monthly_closes
from tests.helpers import register_module_tools
from tests.offline import OfflineClient
from tools.history import stock_day_avg
from utils.errors import UpstreamFormatError

pytestmark = pytest.mark.offline

ROWS = [["114/01/02", "1,065.00"], ["114/01/22", "1,135.00"], ["月平均收盤價", "1102.00"]]
OLD_ROWS = [[" 94/01/03", "51.00"], [" 94/01/31", "52.00"], ["月平均收盤價", "48.51"]]
NOT_FOUND = {"stat": "很抱歉，沒有符合條件的資料!"}


def reply(rows=None, date="20250103", title="114年01月 2330 台積電 日收盤價及月平均收盤價"):
    return {"stat": "OK", "date": date, "title": title, "fields": ["日期", "收盤價"],
            "data": ROWS if rows is None else rows}


def _client(payload):
    return OfflineClient({"/exchangeReport/STOCK_DAY_AVG": payload})


def test_rows_become_closes_and_the_average():
    month = monthly_closes(_client(reply()), "2330", "20250103")
    assert (month.date, month.title) == ("20250103", "114年01月 2330 台積電 日收盤價及月平均收盤價")
    assert [(c.day, c.close) for c in month.closes] == [(date(2025, 1, 2), Decimal("1065.00")),
                                                        (date(2025, 1, 22), Decimal("1135.00"))]
    assert month.average == Decimal("1102.00")
    old = monthly_closes(_client(reply(OLD_ROWS, "20050103")), "2330", "20050103")
    assert old.closes[0].day == date(2005, 1, 3) and old.average == Decimal("48.51")


def test_request_and_no_data():
    seen = []

    def route(params, _body):
        seen.append(dict(params))
        return reply()

    monthly_closes(_client(route), "2330")
    monthly_closes(_client(route), "2330", "20250103")
    assert seen == [{"response": "json", "stockNo": "2330"}, {"response": "json", "stockNo": "2330", "date": "20250103"}]
    assert monthly_closes(_client(NOT_FOUND), "9999") is None


def test_changed_reply_is_an_error():
    with pytest.raises(UpstreamFormatError, match="收盤價"):
        monthly_closes(_client({**reply(), "fields": ["日期", "收盤"]}), "2330", "20250103")
    with pytest.raises(UpstreamFormatError, match="不認得"):
        monthly_closes(_client(reply(ROWS[:2] + [["月均價", "1102.00"]])), "2330", "20250103")
    with pytest.raises(UpstreamFormatError, match="1 欄"):
        monthly_closes(_client(reply([["114/01/02"]])), "2330", "20250103")


def _tool(payload):
    return register_module_tools(stock_day_avg, _client(payload))["get_stock_monthly_average"]


def test_tool_prints_the_same_lines_as_before_the_gateway():
    assert _tool(reply())("2330", "20250103") == (
        "【114年01月 2330 台積電 日收盤價及月平均收盤價】\n\n"
        "日期: 2025-01-02 | 收盤價: 1,065.00\n"
        "日期: 2025-01-22 | 收盤價: 1,135.00\n"
        "月平均收盤價: 1102.00")
    assert "日期: 2005-01-03 | 收盤價: 51.00" in _tool(reply(OLD_ROWS, "20050103"))("2330", "20050103")


def test_tool_reports_no_data():
    assert _tool(NOT_FOUND)("9999") == "查無 9999 在 本月 的月均價資料，請確認該日期為交易日（非假日或週末）"
    assert _tool(reply([]))("2330", "20250103") == "查無 2330 在 202501 的月均價資料"
