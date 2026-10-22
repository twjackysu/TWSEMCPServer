"""sources/twse/bfiauu.py 與 get_block_trades_detail 的單元測試（不打網路）。

上游真實格式由 tests/contract/test_history_tier2_api.py::TestBlockTradesGateway 驗證。
"""

from decimal import Decimal

import pytest

from sources.twse.bfiauu import block_trades
from tests.helpers import register_module_tools
from tests.offline import OfflineClient
from tools.history import block_trades_detail
from utils.errors import UpstreamFormatError

pytestmark = pytest.mark.offline

FIELDS = ["證券代號", "證券名稱", "交易別", "成交價", "成交股數", "成交金額"]
ROWS = [
    ["2330", "台積電", "配對交易", "1,075.00", "1,000,000", "1,075,000,000"],
    ["2308", "台達電", "配對交易", "415.84", "287,920", "119,728,653"],
    ["總計", "", "", "", "1,287,920", "1,194,728,653"],
]
# Until 2011-12-16: 交割期別 between 交易別 and 成交價
OLD_FIELDS = FIELDS[:3] + ["交割期別"] + FIELDS[3:]
OLD_ROWS = [["2454", "聯發科", "配對交易", "T+2日交割", "558.00", "199,020", "111,053,160"],
            ["總計", "", "", "", "", "199,020", "111,053,160"]]


def reply(rows=None, fields=None, **extra):
    return {"stat": "OK", "date": "20250103", "title": "114年01月03日 鉅額交易日成交資訊-單一證券",
            "fields": fields or FIELDS, "data": ROWS if rows is None else rows, **extra}


OLD_REPLY = reply(OLD_ROWS, OLD_FIELDS, date="20100104", title="099年01月04日 鉅額交易日成交資訊-單一證券")


def _day(payload, date="20250103"):
    return block_trades(OfflineClient({"/block/BFIAUU": payload}), date)


def test_trades_become_typed_values_without_the_total():
    day = _day(reply())
    assert (day.date, day.title, len(day.trades)) == ("20250103", "114年01月03日 鉅額交易日成交資訊-單一證券", 2)
    t = day.trades[0]
    assert (t.code, t.name, t.kind, t.settlement) == ("2330", "台積電", "配對交易", "")
    assert (t.price, t.volume, t.value) == (Decimal("1075.00"), 1000000, 1075000000)


def test_until_2011_12_16_the_settlement_column_is_read_by_name():
    (t,) = _day(OLD_REPLY, "20100104").trades
    assert (t.code, t.kind, t.settlement, t.price, t.volume) == ("2454", "配對交易", "T+2日交割", Decimal("558.00"), 199020)


def test_renamed_column_or_row_width_change_is_an_error():
    with pytest.raises(UpstreamFormatError, match="成交價"):
        _day(reply(fields=FIELDS[:3] + ["價格"] + FIELDS[4:]))
    with pytest.raises(UpstreamFormatError, match="6 個"):
        _day(reply([ROWS[0][:5]]))


def test_no_data_is_none_and_a_day_without_block_trades_has_none():
    assert _day({"stat": "查詢日期小於094年04月04日，請重新查詢!"}) is None
    assert _day(reply([])).trades == []


def test_request_parameters():
    seen = {}

    def route(params, _body):
        seen.update(params)
        return reply()

    block_trades(OfflineClient({"/block/BFIAUU": route}), "20250103")
    assert seen == {"response": "json", "date": "20250103"}


def _tool(payload):
    return register_module_tools(block_trades_detail, OfflineClient({"/block/BFIAUU": payload}))["get_block_trades_detail"]


def test_tool_prints_the_same_lines_as_before_the_gateway():
    text = _tool(reply())("20250103")
    assert text.startswith("【114年01月03日 鉅額交易日成交資訊-單一證券】（共 2 筆）\n") and "總計" not in text
    assert "2330 台積電 | 配對交易 | 價:1,075.00 量:1,000,000 金額:1,075,000,000" in text
    assert "2308 台達電 | 配對交易 | 價:415.84 量:287,920 金額:119,728,653" in text


def test_tool_answers_dates_until_2011_12_16_with_the_settlement_period():
    text = _tool(OLD_REPLY)("20100104")
    assert "2454 聯發科 | 配對交易 T+2日交割 | 價:558.00 量:199,020 金額:111,053,160" in text
