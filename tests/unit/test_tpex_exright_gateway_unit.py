"""sources/tpex/ex_daily_q.py 與 get_otc_exright 的單元測試（不打網路）。

上游真實格式由 tests/contract/test_price_analytics_api.py::TestOtcExRightGateway 驗證。
"""

from datetime import date
from decimal import Decimal

import pytest

from sources.tpex.ex_daily_q import otc_exright_results
from tests.helpers import register_module_tools
from tests.offline import OfflineClient
from tools.otc import exright as otc_exright
from utils.errors import UpstreamFormatError

pytestmark = pytest.mark.offline

FIELDS = ["除權息日期", "代號", "名稱", "除權息前收盤價", "除權息參考價", "權值", "息值", "權值+息值", "權/息", "漲停價",
          "跌停價", "開始交易基準價", "減除股利參考價", "現金股利", "每仟股無償配股", "現金增資股數", "現金增資認購價",
          "公開承銷股數", "員工認購股數", "原股東認購股數", "按持股比例仟股認購"]
ROWS = [
    ["115/10/22", "8936", "國統              ", "51.20", "48.20", "0.000000", "3.000000", "3.000000", "除息", "53.00",
     "43.40", "48.20", "48.20", "3.00000000", "0.00000000", "0", "0.00", "0", "0", "0", "0.00000000"],
    ["115/10/23", "4109", "加捷生醫            ", "22.30", "21.58", "0.724292", "0.000000", "0.724292", "除權", "24.50",
     "19.45", "22.30", "22.30", "0.00000000", "0.00000000", "20000000", "18.00", "2000000", "2000000", "16000000",
     "162.04717272"],
]
REPLY = {"date": "20261022~20261023", "stat": "ok", "tables": [{"title": "", "fields": FIELDS, "data": ROWS}]}

# A range starting before 2016: 員工紅利轉增資 sits before 現金增資股數 on every row.
OLD_FIELDS = FIELDS[:15] + ["員工紅利轉增資"] + FIELDS[15:]
OLD_ROWS = [
    ["104/12/01", "8934", "衡平", "44.55", "39.55", "5.00", "0.00000000", "5.00", "除權", "43.50", "35.60", "39.55",
     "39.55", "0.00000000", "126.40329728", "2369.00", "0", "0.00", "0", "0", "0", "0.00000000"],
    ["105/01/07", "4157", "F*太景", "31.60", "31.49", "0.11", "0.00000000", "0.11", "除權", "34.75", "28.35", "31.60",
     "31.60", "0.00000000", "0.00000000", "---", "20000000", "27.50", "2000000", "2000000", "16000000", "22.96341673"],
]
OLD_REPLY = {"date": "20151201~20160131", "stat": "ok", "tables": [{"fields": OLD_FIELDS, "data": OLD_ROWS}]}


def _reply(**table):
    return {**REPLY, "tables": [{**REPLY["tables"][0], **table}]}


def _report(reply, start=None, end=None):
    return otc_exright_results(OfflineClient({"/bulletin/exDailyQ": reply}), start, end)


def test_rows_become_typed_values_with_their_printed_digits():
    report = _report(REPLY)
    assert (report.stat, report.period) == ("ok", "20261022~20261023")
    dividend, rights = report.results
    assert (dividend.day, dividend.code, dividend.name, dividend.kind) == (date(2026, 10, 22), "8936", "國統", "除息")
    assert (dividend.close_before, dividend.reference, dividend.dividend) == (Decimal("51.20"), Decimal("48.20"), 3)
    assert str(dividend.cash_dividend) == "3.00000000" and dividend.cash_capital_shares == 0
    assert (rights.kind, rights.rights, rights.cash_capital_shares, rights.cash_capital_price) == (
        "除權", Decimal("0.724292"), 20000000, Decimal("18.00"))


def test_ranges_before_2016_are_read_by_name_despite_the_extra_column():
    old, spanning = _report(OLD_REPLY).results
    assert (old.code, old.stock_dividend, old.cash_capital_shares) == ("8934", Decimal("126.40329728"), 0)
    assert (spanning.cash_capital_shares, spanning.cash_capital_price) == (20000000, Decimal("27.50"))


def test_renamed_column_is_an_error_not_a_misread():
    with pytest.raises(UpstreamFormatError, match="現金增資股數"):
        _report(_reply(fields=FIELDS[:15] + ["現增股數"] + FIELDS[16:]))


def test_row_width_or_date_format_change_is_an_error():
    with pytest.raises(UpstreamFormatError, match="21 個"):
        _report(_reply(data=[ROWS[0][:20]]))
    with pytest.raises(UpstreamFormatError, match="日期格式"):
        _report(_reply(data=[["2026-10-22"] + ROWS[0][1:]]))


def test_refused_parameters_pass_tpex_reason_on_but_ok_without_tables_is_an_error():
    report = _report({"stat": "參數錯誤"})
    assert (report.stat, report.period, report.results) == ("參數錯誤", "", [])
    with pytest.raises(UpstreamFormatError, match="tables"):
        _report({"stat": "ok", "data": ROWS})


def test_no_results_is_an_empty_report():
    assert _report(_reply(data=[])).results == []


@pytest.mark.parametrize("start,end,expected", [
    (None, None, {"response": "json"}),
    (date(2025, 1, 1), date(2025, 12, 31), {"response": "json", "startDate": "2025/01/01", "endDate": "2025/12/31"}),
])
def test_request_parameters(start, end, expected):
    seen = {}

    def route(params, _body):
        seen.update(params)
        return REPLY

    otc_exright_results(OfflineClient({"/bulletin/exDailyQ": route}), start, end)
    assert seen == expected


def _tool(reply=REPLY):
    return register_module_tools(otc_exright, OfflineClient({"/bulletin/exDailyQ": reply}))["get_otc_exright"]


def test_tool_prints_the_same_lines_as_before_the_gateway():
    text = _tool()()
    assert " 20261022～20261023 上櫃除權除息計算結果" in text
    assert ("115/10/22 | 8936 國統 | 除息 | 前收:51.20 參考價:48.20（權值 0.000000 息值 3.000000）| "
            "現金股利:3.00000000 每仟股配股:0.00000000 | 漲停:53.00 跌停:43.40 開始交易基準價:48.20\n") in text
    assert "加捷生醫 | 除權 |" in text and "開始交易基準價:22.30 | 現增:20000000股@18.00\n" in text


def test_tool_reads_cash_capital_by_name_in_ranges_before_2016():
    text = _tool(OLD_REPLY)("20151201", "20160131")
    assert "開始交易基準價:39.55\n" in text, "8934 沒有現金增資：不該把員工紅利轉增資 2369.00 當成現增股數"
    assert "| 現增:20000000股@27.50\n" in text


def test_tool_filters_by_code_and_reports_an_empty_range():
    text = _tool()(stock_no="4109")
    assert "4109" in text and "8936" not in text
    assert _tool(_reply(data=[]))("20261017", "20261018") == "查無 20261022～20261023 的上櫃除權息資料"
    assert _tool({"stat": "參數錯誤"})("20261018", "20261001") == "查無 指定期間 的上櫃除權息資料"
