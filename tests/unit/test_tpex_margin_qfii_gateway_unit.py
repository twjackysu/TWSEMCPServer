"""sources/tpex/margin_balance.py、sources/tpex/qfii.py 與 get_otc_margin_balance／get_otc_foreign_holdings 的單元測試
（不打網路）。

欄位、summary 與資料列取自櫃買中心真實回應（2010-01-04、2014-01-02、2025-01-03）；上游真實格式由
tests/contract/test_otc_history_api.py 的 TestOtcMarginGateway / TestOtcForeignHoldingsGateway 驗證。
"""

from decimal import Decimal

import pytest

from sources.tpex.margin_balance import otc_margin_balances
from sources.tpex.qfii import otc_foreign_holdings
from tests.helpers import register_module_tools
from tests.offline import OfflineClient
from tools.otc import history as otc_history, valuation_holdings
from utils.errors import UpstreamFormatError

pytestmark = pytest.mark.offline

MARGIN_FIELDS = ["代號", "名稱", "前資餘額(張)", "資買", "資賣", "現償", "資餘額", "資屬證金", "資使用率(%)", "資限額",
                 "前券餘額(張)", "券賣", "券買", "券償", "券餘額", "券屬證金", "券使用率(%)", "券限額", "資券相抵(張)", "備註"]
MARGIN_ROWS = [["00679B", "元大美債20年", "28,292", "63", "445", "14", "27,896", "235", "1.04", "2,658,048",
                "2", "0", "1", "0", "1", "0", "0.0", "2,658,048", "2", ""],
               ["1333", "恩得利", "200", "0", "3", "0", "197", "0", "0.93", "21,275",
                "0", "0", "0", "0", "0", "0", "0.0", "21,275", "0", "$OX"]]
MARGIN_SUMMARY = [["", "合計(張)", "2,474,629", "52,829", "68,993", "1,502", "2,456,963", "", "", "", "93,755", "7,467",
                   "5,899", "439", "94,884", "", "", "", "", ""],
                  ["", "融資金(仟元)", "117,038,761", "3,012,842", "4,158,445", "66,087", "115,827,071", "", "", "", "",
                   "", "", "", "", "", "", "", "", ""]]
QFII_FIELDS = ["排行", "代號", "名稱", "發行股數(A)", "僑外資及陸資尚可投資股數B=A*F-C", "僑外資及陸資持有股數(C)",
               "僑外資及陸資尚可投資比率(D=B/A)", "僑外資及陸資持股比率(E=C/A)", "法令投資上限比率(F)", "備註"]
QFII_ROWS = [["1", "8455", "大拓-KY", "25,219,056", "3,059,750", "22,159,306", "12.13%", "87.86%", "100%", ""],
             ["2", "8406", "F-金可", "90,451,000", "0", "90,451,000", "0%", "100%", "100%", "已達上限"]]


def reply(fields, rows, summary=None):
    return {"stat": "ok", "date": "20250103", "tables": [
        {"title": "表", "fields": fields, "data": rows, "summary": summary or [], "notes": [], "totalCount": len(rows)}]}


def margin_reply(rows=None, summary=None, fields=None):
    return reply(fields or MARGIN_FIELDS, MARGIN_ROWS if rows is None else rows,
                 MARGIN_SUMMARY if summary is None else summary)


def qfii_reply(rows=None, fields=None):
    return reply(fields or QFII_FIELDS, QFII_ROWS if rows is None else rows)


def _client(path, payload):
    return OfflineClient({path: payload})


def test_margin_rows_and_totals_become_typed():
    day = otc_margin_balances(_client("/margin/balance", margin_reply()), "20250103")
    etf, old = day.balances
    assert (etf.code, etf.name, etf.offset, etf.note) == ("00679B", "元大美債20年", 2, "")
    m, s = etf.margin, etf.short
    assert (m.previous, m.buy, m.sell, m.repaid, m.balance, m.finance, m.usage, m.limit) == (
        28292, 63, 445, 14, 27896, 235, Decimal("1.04"), 2658048)
    assert (s.previous, s.sell, s.buy, s.repaid, s.balance, s.usage) == (2, 0, 1, 0, 1, Decimal("0.0"))
    assert old.note == "$OX"
    assert [(t.label, t.margin_balance, t.short_balance) for t in day.totals] == [
        ("合計(張)", 2456963, 94884), ("融資金(仟元)", 115827071, None)]


def test_padded_codes_are_stripped():
    padded = [["1259  ", "安心"] + MARGIN_ROWS[1][2:-1] + ["11     C"]]
    (b,) = otc_margin_balances(_client("/margin/balance", margin_reply(padded, [])), "20140102").balances
    assert (b.code, b.note) == ("1259", "11     C")


def test_qfii_rows_become_typed_with_their_percent_signs_dropped():
    first, capped = otc_foreign_holdings(_client("/insti/qfii", qfii_reply()), "20250103").holdings
    assert (first.rank, first.code, first.issued_shares, first.available_shares, first.held_shares) == (
        1, "8455", 25219056, 3059750, 22159306)
    assert (first.available_pct, first.held_pct, first.limit_pct) == (Decimal("12.13"), Decimal("87.86"), Decimal("100"))
    assert (capped.available_pct, capped.note) == (Decimal("0"), "已達上限")


def test_requests_no_data_and_changed_fields():
    seen = []

    def route(params, _body):
        seen.append(dict(params))
        return qfii_reply()

    otc_foreign_holdings(_client("/insti/qfii", route))
    otc_foreign_holdings(_client("/insti/qfii", route), "20250103")
    assert seen == [{"response": "json"}, {"response": "json", "date": "2025/01/03"}]
    assert otc_margin_balances(_client("/margin/balance", margin_reply([], [])), "20260927").balances == []
    with pytest.raises(UpstreamFormatError, match="券使用率"):
        otc_margin_balances(_client("/margin/balance", margin_reply(fields=MARGIN_FIELDS[:16] + ["券使用率"] +
                                                                     MARGIN_FIELDS[17:])), "20250103")
    with pytest.raises(UpstreamFormatError, match="9 欄"):
        otc_foreign_holdings(_client("/insti/qfii", qfii_reply([QFII_ROWS[0][:9]])), "20250103")
    with pytest.raises(UpstreamFormatError, match="tables"):
        otc_foreign_holdings(_client("/insti/qfii", {"stat": "ok"}), "20250103")


def test_margin_tool_prints_the_same_lines_as_before_the_gateway():
    fn = register_module_tools(otc_history, _client("/margin/balance", margin_reply()))["get_otc_margin_balance"]
    text = fn("20250103")
    assert ("00679B 元大美債20年 | 融資: 前日28,292 買63 賣445 現償14 餘額27,896 使用率1.04% 限額2,658,048 | "
            "融券: 前日2 賣0 買1 券償0 餘額1 使用率0.0% | 資券相抵2\n") in text
    assert "1333 恩得利 | 融資: 前日200 買0 賣3 現償0 餘額197 使用率0.93% 限額21,275 | " in text
    assert "資券相抵0 | 備註:$OX\n" in text
    assert text.endswith("全市場合計: 合計(張) 資餘額2,456,963 券餘額94,884 / 融資金(仟元) 資餘額115,827,071")
    filtered = fn("20250103", stock_no="1333")
    assert "全市場合計" not in filtered and "共有 1 筆" in filtered


def test_qfii_tool_prints_the_same_lines_as_before_and_filters_on_the_code_not_the_rank():
    fn = register_module_tools(valuation_holdings, _client("/insti/qfii", qfii_reply()))["get_otc_foreign_holdings"]
    text = fn()
    assert ("#1 8455 大拓-KY | 外資持股比率:87.86% | 尚可投資比率:12.13% | 投資上限:100% | 持有股數:22,159,306 | "
            "發行股數:25,219,056\n") in text
    assert "#2 8406 F-金可 | 外資持股比率:100% | 尚可投資比率:0% | 投資上限:100% | 持有股數:90,451,000 | " \
           "發行股數:90,451,000 | 備註:已達上限\n" in text
    assert "8455" not in fn(stock_no="8406") and "查無符合條件" in fn(stock_no="1")
