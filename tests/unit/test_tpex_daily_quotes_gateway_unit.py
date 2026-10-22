"""sources/tpex/daily_quotes.py 與 get_otc_daily（帶 date）的單元測試（不打網路）。

上游真實格式由 tests/contract/test_otc_history_api.py::TestOTCDailyQuotesGateway 驗證。
"""

from decimal import Decimal

import pytest

from sources.tpex.daily_quotes import otc_daily_quotes
from tests.helpers import register_module_tools
from tests.offline import OfflineClient
from tools.otc import daily_close
from utils.errors import UpstreamFormatError

pytestmark = pytest.mark.offline

# From 2020-04-30: 最後買量 / 最後賣量 between the prices (unit label 千股 or 張數 depending on the day)
FIELDS = ["代號", "名稱", "收盤 ", "漲跌", "開盤 ", "最高 ", "最低", "成交股數  ", " 成交金額(元)", " 成交筆數 ", "最後買價",
          "最後買量<br>(千股)", "最後賣價", "最後賣量<br>(千股)", "發行股數 ", "次日漲停價 ", "次日跌停價"]
ROWS = [
    ["5274", "信驊", "4,545.00", "+60.00", "4,500.00", "4,560.00", "4,480.00", "312,000", "1,416,630,000", "1,234",
     "4,540.00", "3", "4,545.00", "5", "37,662,000", "4,995.00", "4,090.00"],
    ["6741", "91APP*-KY", "----", "---", "----", "----", "----", "0", "0", "0", "88.00", "2", "89.00", "1",
     "112,000,000", "98.40", "80.60"],
]
REPLY = {"date": "20250103", "stat": "ok", "tables": [{"title": "上櫃股票每日收盤行情(不含定價)", "fields": FIELDS, "data": ROWS}]}

# Before 2020-04-30: no 最後買量 / 最後賣量, so 最後賣價 is the 12th column and 發行股數 the 13th.
OLD_FIELDS = FIELDS[:11] + [FIELDS[12]] + FIELDS[14:]
OLD_ROWS = [["01006T", "基泰SR", "8.00", "- 0.19", "8.03", "8.10", "8.00", "31,000", "249,080", "11", "7.97", "8.00",
             "247,000,000", "8.56", "7.44"],
            ["5274", "信驊", "1430.00", "+ 5.00", "1425.00", "1440.00", "1420.00", "45,000", "64,215,000", "55",
             "1425.00", "1430.00", "33,262,000", "1570.00", "1290.00"]]
OLD_REPLY = {"date": "20150105", "stat": "ok", "tables": [{"fields": OLD_FIELDS, "data": OLD_ROWS}]}


def _reply(**table):
    return {**REPLY, "tables": [{**REPLY["tables"][0], **table}]}


def _day(reply, date="20250103", security_type="EW"):
    return otc_daily_quotes(OfflineClient({"/afterTrading/otc": reply}), date, security_type)


def test_rows_become_typed_values_found_by_name():
    day = _day(REPLY)
    assert (day.date, day.group) == ("20250103", "")
    traded, untraded = day.quotes
    assert (traded.code, traded.name, traded.change) == ("5274", "信驊", "+60.00")
    assert traded.close == Decimal("4545.00") and (traded.last_bid, traded.last_ask) == (Decimal("4540.00"), Decimal("4545.00"))
    assert (traded.volume, traded.value, traded.transactions) == (312000, 1416630000, 1234)
    assert (untraded.close, untraded.open, untraded.change, untraded.volume) == (None, None, "---", 0)


def test_before_2020_04_30_the_last_ask_is_read_by_name():
    old_lot, high_price = _day(OLD_REPLY, "20150105").quotes
    assert (old_lot.last_bid, old_lot.last_ask, old_lot.change) == (Decimal("7.97"), Decimal("8.00"), "- 0.19")
    assert high_price.last_ask == Decimal("1430.00")


def test_renamed_column_or_row_width_change_is_an_error():
    with pytest.raises(UpstreamFormatError, match="最後賣價"):
        _day(_reply(fields=FIELDS[:12] + ["最後委賣價"] + FIELDS[13:]))
    with pytest.raises(UpstreamFormatError, match="17 個"):
        _day(_reply(data=[ROWS[0][:15]]))
    with pytest.raises(UpstreamFormatError, match="tables"):
        _day({"stat": "ok", "data": ROWS})


def test_no_trading_is_none():
    assert _day(_reply(data=[])) is None


def test_industry_code_names_its_group_and_latest_day_sends_no_date():
    seen = {}

    def route(params, _body):
        seen.update(params)
        return _reply(category="半導體類")

    day = otc_daily_quotes(OfflineClient({"/afterTrading/otc": route}), "", "24")
    assert seen == {"type": "24", "response": "json"} and day.group == "半導體類"
    otc_daily_quotes(OfflineClient({"/afterTrading/otc": route}), "20250103")
    assert seen == {"type": "EW", "response": "json", "date": "2025/01/03"}


def _tool(reply):
    return register_module_tools(daily_close, OfflineClient({"/afterTrading/otc": reply}))["get_otc_daily"]


def test_tool_prints_the_same_lines_as_before_the_gateway():
    text = _tool(REPLY)("20250103")
    assert " 20250103 上櫃股票及 ETF收盤行情（成交量值不含定價交易）" in text
    assert ("5274 信驊 | 收: 4,545.00 | 漲跌: +60.00 | 開: 4,500.00 | 高: 4,560.00 | 低: 4,480.00 | 量: 312,000 | "
            "金額: 1,416,630,000 | 筆數: 1,234 | 最後買/賣: 4,540.00/4,545.00\n") in text
    assert ("6741 91APP*-KY | 收: ---- | 漲跌: --- | 開: ---- | 高: ---- | 低: ---- | 量: 0 | 金額: 0 | 筆數: 0 | "
            "最後買/賣: 88.00/89.00\n") in text


def test_tool_shows_the_last_ask_before_2020_04_30_not_the_shares_issued():
    text = _tool(OLD_REPLY)("20150105", stock_no="01006T")
    assert "| 漲跌: - 0.19 |" in text and "最後買/賣: 7.97/8.00\n" in text and "247,000,000" not in text
