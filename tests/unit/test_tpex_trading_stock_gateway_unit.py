"""sources/tpex/trading_stock.py 與 get_otc_stock_history 的單元測試（不打網路）。

上游真實格式由 tests/contract/test_otc_history_api.py::TestOTCTradingStockGateway 驗證。
"""

from datetime import date
from decimal import Decimal

import pytest

from sources.tpex.trading_stock import trading_stock_month
from tests.helpers import register_module_tools
from tests.offline import OfflineClient
from tools.otc import history as otc_history
from utils.errors import UpstreamFormatError

pytestmark = pytest.mark.offline

FIELDS = ["日 期", "成交張數", "成交仟元", "開盤", "最高", "最低", "收盤", "漲跌", "筆數"]
ROWS = [
    ["115/10/01", "24,330", "26,580,157", "1,055.00", "1,135.00", "1,045.00", "1,085.00", "50.00", "39,220"],
    ["115/10/02", "0", "0", "--", "--", "--", "--", "0.00", "0"],
]
REPLY = {"stat": "ok", "date": "20261001", "code": "6488", "name": "環球晶",
         "tables": [{"title": "個股日成交資訊", "fields": FIELDS, "data": ROWS}]}
EMPTY = {"stat": "ok", "date": "20261001", "code": "2330", "name": "", "tables": [{"fields": FIELDS, "data": []}]}


def _reply(**table):
    return {**REPLY, "tables": [{**REPLY["tables"][0], **table}]}


def _month(reply, code="6488"):
    return trading_stock_month(OfflineClient({"/afterTrading/tradingStock": reply}), code, 2026, 10)


def test_rows_become_typed_values_with_their_printed_digits():
    month = _month(REPLY)
    assert (month.code, month.name) == ("6488", "環球晶")
    first, untraded = month.rows
    assert first.day == date(2026, 10, 1)
    assert (first.lots, first.value_thousands, first.transactions) == (24330, 26580157, 39220)
    assert first.close == Decimal("1085.00") and str(first.close) == "1085.00"
    assert first.change == "50.00"
    assert (untraded.open, untraded.close, untraded.lots) == (None, None, 0)


def test_columns_are_found_by_name_not_position():
    order = [8, 7, 6, 5, 4, 3, 2, 1, 0]
    reply = _reply(fields=[FIELDS[i] for i in order], data=[[r[i] for i in order] for r in ROWS])
    assert _month(reply).rows == _month(REPLY).rows


def test_spaces_in_a_column_name_do_not_matter():
    assert _month(_reply(fields=["日期"] + FIELDS[1:])).rows == _month(REPLY).rows


def test_months_before_2025_name_the_volume_column_thousand_shares():
    assert _month(_reply(fields=["日 期", "成交仟股"] + FIELDS[2:])).rows == _month(REPLY).rows


def test_renamed_column_is_an_error_not_a_misread():
    with pytest.raises(UpstreamFormatError, match="成交張數"):
        _month(_reply(fields=["日 期", "成交股數"] + FIELDS[2:]))


def test_row_width_or_date_format_change_is_an_error():
    with pytest.raises(UpstreamFormatError, match="9 個"):
        _month(_reply(data=[ROWS[0] + ["新欄位"]]))
    with pytest.raises(UpstreamFormatError, match="日期格式"):
        _month(_reply(data=[["2026-10-01"] + ROWS[0][1:]]))


def test_reply_without_tables_is_an_error():
    with pytest.raises(UpstreamFormatError, match="tables"):
        _month({"stat": "ok", "data": ROWS})


def test_no_data_is_none():
    assert _month(EMPTY, code="2330") is None
    assert _month({**EMPTY, "tables": []}, code="2330") is None


def test_requests_the_first_of_the_month():
    seen = {}

    def route(params, _body):
        seen.update(params)
        return REPLY

    trading_stock_month(OfflineClient({"/afterTrading/tradingStock": route}), "6488", 2026, 10)
    assert seen == {"code": "6488", "date": "2026/10/01", "response": "json"}


def _tool(reply=REPLY):
    return register_module_tools(otc_history, OfflineClient({"/afterTrading/tradingStock": reply}))["get_otc_stock_history"]


def test_tool_prints_the_same_lines_as_before_the_gateway():
    text = _tool()("6488", "20261015")
    assert text.splitlines()[0] == "【6488 環球晶 上櫃個股日成交資訊 2026-10】（共 2 個交易日）"
    assert ("115/10/01 | 開:1,055.00 高:1,135.00 低:1,045.00 收:1,085.00 漲跌:50.00 | "
            "量:24,330張 值:26,580,157仟元 筆數:39,220") in text
    assert "115/10/02 | 開:-- 高:-- 低:-- 收:-- 漲跌:0.00 | 量:0張 值:0仟元 筆數:0" in text


def test_tool_prints_pre_2011_dates_as_tpex_does():
    reply = _reply(data=[["99/12/01", "11,053", "1,111,521", "102.50", "102.50", "99.60", "100.00", "-3.00", "5,326"]])
    assert _tool(reply)("5483", "20101201").splitlines()[1].startswith("99/12/01 | 開:102.50")


def test_tool_reports_a_code_tpex_does_not_trade():
    assert "請確認為上櫃股票代號" in _tool(EMPTY)("2330", "20261001")
