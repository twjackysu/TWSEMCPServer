"""sources/twse/twt93u.py 與 get_short_sale_lending_balance_history 的單元測試（不打網路）。

上游真實格式由 tests/contract/test_history_tier2_api.py::TestShortSaleLendingGateway 驗證。
"""

import pytest

from sources.twse.twt93u import short_sale_lending_balances
from tests.helpers import register_module_tools
from tests.offline import OfflineClient
from tools.history import short_sale_lending
from utils.errors import UpstreamFormatError

pytestmark = pytest.mark.offline

FIELDS = ["代號", "名稱", "前日餘額", "賣出", "買進", "現券", "今日餘額", "次一營業日限額",
          "前日餘額", "當日賣出", "當日還券", "當日調整", "當日餘額", "次一營業日可限額", "備註"]
GROUPS = [{"title": "股票", "span": 2}, {"title": "融券", "span": 6}, {"title": "借券賣出", "span": 6}, {"title": "", "span": 1}]
ROWS = [
    ["0050", "元大台灣50", "1,909,000", "48,000", "77,000", "0", "1,880,000", "283,875,000",
     "11,205,000", "0", "2,000,000", "-34,000", "9,171,000", "2,116,582", "XZ "],
    ["", "合計", "1", "1", "1", "1", "1", "0", "1", "1", "1", "1", "1", "0", " "],
]
# Until 2012-03-16: 借券賣出 is 前日餘額, 賣出, 庫存異動 (signed), 今日餘額, 可使用額度 — five columns
OLD_FIELDS = FIELDS[:8] + ["前日餘額", "賣出", "庫存異動", "今日餘額", "可使用額度", "備註"]
OLD_GROUPS = GROUPS[:2] + [{"title": "借券賣出", "span": 5}, {"title": "", "span": 1}]
OLD_ROWS = [["0015", "富邦", "0", "0", "0", "0", "0", "125,000,000", "962,000", "14,000", "-2,000", "974,000", "41,739,026", " "]]


def reply(rows=None, fields=None, groups=None, **extra):
    return {"stat": "OK", "date": "20150105", "title": "104年01月05日 信用額度總量管制餘額表", "hints": "單位：股",
            "fields": fields or FIELDS, "groups": groups or GROUPS, "data": ROWS if rows is None else rows, **extra}


OLD_REPLY = reply(OLD_ROWS, OLD_FIELDS, OLD_GROUPS, date="20100104", title="099年01月04日 信用額度總量管制餘額表")


def _day(payload):
    return short_sale_lending_balances(OfflineClient({"/marginTrading/TWT93U": payload}), "20150105")


def test_rows_are_read_by_group_and_name_without_the_total():
    day = _day(reply())
    assert (day.date, day.title, len(day.rows)) == ("20150105", "104年01月05日 信用額度總量管制餘額表", 1)
    r = day.rows[0]
    assert (r.code, r.name, r.note) == ("0050", "元大台灣50", "XZ")
    assert (r.short.previous, r.short.sold, r.short.bought, r.short.today) == (1909000, 48000, 77000, 1880000)
    b = r.lending
    assert (b.previous, b.sold, b.returned, b.adjusted, b.today, b.next_day_limit) == (
        11205000, 0, 2000000, -34000, 9171000, 2116582)
    assert not b.old_layout and b.inventory_change is None and b.available is None


def test_until_2012_03_16_the_lending_group_keeps_its_own_columns():
    b = _day(OLD_REPLY).rows[0].lending
    assert b.old_layout
    assert (b.previous, b.sold, b.inventory_change, b.today, b.available) == (962000, 14000, -2000, 974000, 41739026)
    assert b.returned is None and b.adjusted is None and b.next_day_limit is None


def test_groups_that_do_not_cover_the_fields_or_a_renamed_column_are_errors():
    with pytest.raises(UpstreamFormatError, match="groups"):
        _day(reply(groups=GROUPS[:3]))
    with pytest.raises(UpstreamFormatError, match="借券賣出/當日還券"):
        _day(reply(fields=FIELDS[:10] + ["還券"] + FIELDS[11:]))
    with pytest.raises(UpstreamFormatError, match="15 個"):
        _day(reply([ROWS[0][:14]]))


def test_no_data_is_none_and_an_empty_day_has_no_rows():
    assert _day({"stat": "查詢日期小於94年7月1日，請重新查詢!", "total": 0}) is None
    assert _day(reply([])).rows == []


def test_request_parameters():
    seen = {}

    def route(params, _body):
        seen.update(params)
        return reply()

    short_sale_lending_balances(OfflineClient({"/marginTrading/TWT93U": route}), "20150105")
    assert seen == {"response": "json", "date": "20150105", "selectType": "ALL"}


def _tool(payload):
    tools = register_module_tools(short_sale_lending, OfflineClient({"/marginTrading/TWT93U": payload}))
    return tools["get_short_sale_lending_balance_history"]


def test_tool_prints_the_same_lines_as_before_the_gateway():
    text = _tool(reply())("20150105")
    assert text.startswith("【104年01月05日 信用額度總量管制餘額表】（共 1 筆）\n") and "合計" not in text
    assert ("0050 元大台灣50\n"
            "  融券: 前日1,909,000 賣出48,000 買進77,000 現券0 今日1,880,000 次日限額283,875,000\n"
            "  借券: 前日11,205,000 當日賣出0 當日還券2,000,000 調整-34,000 當日9,171,000 次日可限額2,116,582") in text


def test_tool_shows_the_published_lending_columns_until_2012_03_16():
    text = _tool(OLD_REPLY)("20100104")
    assert "  借券: 前日962,000 賣出14,000 庫存異動-2,000 今日974,000 可使用額度41,739,026" in text
