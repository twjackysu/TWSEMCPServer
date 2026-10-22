"""sources/tpex/pe_qry_date.py 與 get_otc_valuation 的單元測試（不打網路）。

上游真實格式由 tests/contract/test_otc_history_api.py::TestOTCValuationGateway 驗證。
"""

from decimal import Decimal

import pytest

from sources.tpex.pe_qry_date import otc_valuation_ratios
from tests.helpers import register_module_tools
from tests.offline import OfflineClient
from tools.otc import valuation_holdings
from utils.errors import UpstreamFormatError

pytestmark = pytest.mark.offline

FIELDS = ["股票代號", "公司名稱", "本益比", "每股股利", "股利年度", "殖利率(%)", "股價淨值比", "財報年/季"]
ROWS = [
    ["1240", "茂生農經        ", "11.78", "3.40000000", 113, "5.15", "1.17", "113Q3"],
    ["3105", "穩懋            ", "N/A", "0.00000000", 113, "0.00", "2.10", "113Q3"],
    ["8299", "群聯            ", "11125.00", "36.00000000", 113, "2.47", "N/A", "113Q3"],
]
REPLY = {"date": "20250103", "stat": "ok", "tables": [{"fields": FIELDS, "data": ROWS}]}
# Before 2025-01-02: no 財報年/季
OLD_REPLY = {"date": "20180102", "stat": "ok",
             "tables": [{"fields": FIELDS[:7], "data": [["1258", "其祥-KY         ", "16.51", "0.50000000", 106, "4.28", "1.31"]]}]}


def _report(reply, date="20250103"):
    return otc_valuation_ratios(OfflineClient({"/afterTrading/peQryDate": reply}), date)


def test_rows_become_typed_values():
    report = _report(REPLY)
    assert report.date == "20250103"
    first, loss, high_pe = report.valuations
    assert (first.code, first.name, first.dividend_year, first.fiscal) == ("1240", "茂生農經", "113", "113Q3")
    assert (first.pe, first.dividend_per_share, first.dividend_yield, first.pb) == (
        Decimal("11.78"), Decimal("3.40000000"), Decimal("5.15"), Decimal("1.17"))
    assert loss.pe is None and high_pe.pb is None and high_pe.pe == Decimal("11125.00")


def test_before_2025_there_is_no_fiscal_column():
    (v,) = _report(OLD_REPLY, "20180102").valuations
    assert (v.code, v.pe, v.dividend_year, v.fiscal) == ("1258", Decimal("16.51"), "106", "")


def test_renamed_column_or_row_width_change_is_an_error():
    with pytest.raises(UpstreamFormatError, match="殖利率"):
        _report({**REPLY, "tables": [{"fields": FIELDS[:5] + ["殖利率"] + FIELDS[6:], "data": ROWS}]})
    with pytest.raises(UpstreamFormatError, match="8 個"):
        _report({**REPLY, "tables": [{"fields": FIELDS, "data": [ROWS[0][:7]]}]})
    with pytest.raises(UpstreamFormatError, match="tables"):
        _report({"stat": "ok"})


def test_a_day_without_trading_has_no_valuations_but_keeps_its_date():
    report = _report({"date": "20250104", "stat": "ok", "tables": [{"fields": FIELDS, "data": []}]}, "20250104")
    assert (report.date, report.valuations) == ("20250104", [])


def test_latest_day_sends_no_date():
    seen = {}

    def route(params, _body):
        seen.update(params)
        return REPLY

    otc_valuation_ratios(OfflineClient({"/afterTrading/peQryDate": route}))
    assert seen == {"response": "json"}
    otc_valuation_ratios(OfflineClient({"/afterTrading/peQryDate": route}), "20250103")
    assert seen == {"response": "json", "date": "2025/01/03"}


def _tool(reply):
    return register_module_tools(valuation_holdings, OfflineClient({"/afterTrading/peQryDate": reply}))["get_otc_valuation"]


def test_tool_prints_the_same_lines_as_before_the_gateway():
    text = _tool(REPLY)("20250103")
    assert " 20250103 上櫃股票本益比、殖利率及股價淨值比" in text
    assert "1240 茂生農經 | 本益比: 11.78 | 殖利率: 5.15%（每股股利 3.40000000，股利年度 113）| 股價淨值比: 1.17（財報 113Q3）\n" in text
    assert "3105 穩懋 | 本益比: N/A | 殖利率: 0.00%（每股股利 0.00000000，股利年度 113）| 股價淨值比: 2.10（財報 113Q3）\n" in text
    assert "8299 群聯 | 本益比: 11125.00 |" in text and "股價淨值比: N/A（財報 113Q3）" in text


def test_tool_answers_dates_before_2025():
    text = _tool(OLD_REPLY)("20180102", stock_no="1258")
    assert "1258 其祥-KY | 本益比: 16.51 | 殖利率: 4.28%（每股股利 0.50000000，股利年度 106）| 股價淨值比: 1.31\n" in text
