"""sources/twse/mi_margn.py 與 get_margin_balance 的單元測試（不打網路）。

表格的 title、groups、fields、個股列與融資兩列統計取自證交所真實回應（2014-01-02、2025-01-03；融券統計列的數字
是編的）；上游真實格式由
tests/contract/test_history_api.py::TestMarginBalanceGateway 驗證。
"""

from datetime import datetime

import pytest

from sources.twse.mi_margn import margin_balances
from tests.helpers import register_module_tools
from tests.offline import OfflineClient
from tools.history import margin_balance
from utils.errors import UpstreamFormatError

pytestmark = pytest.mark.offline

SUMMARY_FIELDS = ["項目", "買進", "賣出", "現金(券)償還", "前日餘額", "今日餘額"]
TOTALS = [["融資(交易單位)", "209,142", "218,874", "4,722", "8,738,199", "8,723,745"],
          ["融券(交易單位)", "15,330", "14,207", "1,103", "236,553", "236,533"],
          ["融資金額(仟元)", "9,527,832", "11,034,630", "167,072", "329,543,807", "327,869,937"]]
GROUPS = [{"title": "股票", "span": 2}, {"title": "融資", "span": 6}, {"title": "融券", "span": 6},
          {"title": "", "span": 1}, {"title": "", "span": 1}]
FIELDS = ["代號", "名稱", "買進", "賣出", "現金償還", "前日餘額", "今日餘額", "次一營業日限額",
          "買進", "賣出", "現券償還", "前日餘額", "今日餘額", "次一營業日限額", "資券互抵", "註記"]
ROWS = [["0050", "元大台灣50", "22", "41", "0", "929", "910", "554,750", "5", "11", "0", "211", "217", "554,750", "0", " "],
        ["0015", "富邦", "0", "0", "0", "2,107", "2,107", "125,000", "0", "0", "0", "0", "0", "125,000", "0", "OX "]]


def reply(rows=None, totals=None, date="20250103"):
    return {"stat": "OK", "date": date, "tables": [
        {"title": "114年01月03日 信用交易統計", "fields": SUMMARY_FIELDS, "data": TOTALS if totals is None else totals},
        {"title": "114年01月03日 融資融券彙總 (全部)", "groups": GROUPS, "fields": FIELDS,
         "data": ROWS if rows is None else rows, "notes": []}]}


NOT_A_TRADING_DAY = {"stat": "很抱歉，沒有符合條件的資料!"}


def _client(payload):
    return OfflineClient({"/exchangeReport/MI_MARGN": payload})


def test_tables_become_typed_totals_and_balances():
    day = margin_balances(_client(reply()), "20250103")
    assert day.date == "20250103"
    assert [(t.item, t.buy, t.today) for t in day.totals] == [
        ("融資(交易單位)", 209142, 8723745), ("融券(交易單位)", 15330, 236533), ("融資金額(仟元)", 9527832, 327869937)]
    etf, old = day.balances
    assert (etf.code, etf.name, etf.offset, etf.note) == ("0050", "元大台灣50", 0, " ")
    m, s = etf.margin, etf.short
    assert (m.buy, m.sell, m.repaid, m.previous, m.today, m.next_day_limit) == (22, 41, 0, 929, 910, 554750)
    assert (s.buy, s.sell, s.repaid, s.previous, s.today, s.next_day_limit) == (5, 11, 0, 211, 217, 554750)
    assert old.note == "OX "


def test_tables_are_found_by_fields_and_columns_by_group():
    swapped = reply()
    swapped["tables"].reverse()
    assert margin_balances(_client(swapped), "20250103") == margin_balances(_client(reply()), "20250103")


def test_latest_day_and_no_data():
    seen = []

    def route(params, _body):
        seen.append(dict(params))
        return reply()

    margin_balances(_client(route))
    assert seen == [{"response": "json", "selectType": "ALL"}]
    assert margin_balances(_client(NOT_A_TRADING_DAY), "20260927") is None
    assert margin_balances(_client({"stat": "OK", "tables": [{"data": []}, {"data": []}]}), "20260927").balances == []


def test_changed_tables_are_an_error():
    renamed = reply()
    renamed["tables"][1]["groups"] = GROUPS[:2] + [{"title": "借券", "span": 6}] + GROUPS[3:]
    with pytest.raises(UpstreamFormatError, match="融券/買進"):
        margin_balances(_client(renamed), "20250103")
    no_code = reply()
    no_code["tables"][1]["fields"] = ["股票代號"] + FIELDS[1:]
    with pytest.raises(UpstreamFormatError, match="找不到個股明細表"):
        margin_balances(_client(no_code), "20250103")
    with pytest.raises(UpstreamFormatError, match="15 欄"):
        margin_balances(_client(reply([ROWS[0][:15]])), "20250103")


def _tool(payload):
    return register_module_tools(margin_balance, _client(payload))["get_margin_balance"]


def test_tool_prints_the_same_lines_as_before_the_gateway():
    text = _tool(reply())("20250103")
    assert text.startswith(
        "【融資融券餘額 - 20250103】（共 2 筆）\n\n"
        "全市場信用交易統計（買進/賣出/償還/前日餘額/今日餘額）:\n"
        "  融資(交易單位) | 209,142 | 218,874 | 4,722 | 8,738,199 | 8,723,745\n")
    assert ("欄位: 代號 | 名稱 | 買進 | 賣出 | 現金償還 | 前日餘額 | 今日餘額 | 次一營業日限額 | 買進 | 賣出 | 現券償還 | "
            "前日餘額 | 今日餘額 | 次一營業日限額 | 資券互抵 | 註記\n\n"
            "0050 | 元大台灣50 | 22 | 41 | 0 | 929 | 910 | 554,750 | 5 | 11 | 0 | 211 | 217 | 554,750 | 0 |  \n"
            "0015 | 富邦 | 0 | 0 | 0 | 2,107 | 2,107 | 125,000 | 0 | 0 | 0 | 0 | 0 | 125,000 | 0 | OX ") in text


def test_tool_walks_back_to_a_trading_day_and_filters():
    asked = []

    def route(params, _body):
        asked.append(params["date"])
        return reply(date="20250103") if params["date"] == "20250103" else NOT_A_TRADING_DAY

    fn = _tool(route)
    text = fn("20250105", stock_no="0015")
    assert asked == ["20250105", "20250104", "20250103"]
    assert "（原查詢 20250105，實際資料日 20250103）" in text and "共 1 筆" in text and "全市場信用交易統計" not in text
    assert "查無名稱包含「台積」" in fn("20250103", name="台積")
    assert fn(f"{datetime(2026, 9, 27):%Y%m%d}") == "查無 20260927 前後的融資融券資料"
