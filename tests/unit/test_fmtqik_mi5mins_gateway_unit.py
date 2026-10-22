"""sources/twse/fmtqik.py、sources/twse/mi_5mins_hist.py 與 get_market_turnover_history／get_taiex_index_history
的單元測試（不打網路）。

欄位與資料列取自證交所真實回應（2005-01 與 2025-01）；上游真實格式由 tests/contract/test_history_tier1_api.py 的
TestMarketTurnoverGateway / TestTaiexHistoryGateway 驗證。
"""

from datetime import date
from decimal import Decimal

import pytest

from sources.twse.fmtqik import market_turnover
from sources.twse.mi_5mins_hist import taiex_history
from tests.helpers import register_module_tools
from tests.offline import OfflineClient
from tools.history import market_turnover as market_turnover_tool, taiex_index_history
from utils.errors import UpstreamFormatError

pytestmark = pytest.mark.offline

TURNOVER_FIELDS = ["日期", "成交股數", "成交金額", "成交筆數", "發行量加權股價指數", "漲跌點數"]
TURNOVER = [[" 94/01/03", "4,227,307,000", "75,449,754,940", "637,322", "6,143.12", "3.43"],
            ["114/01/02", "6,901,476,303", "379,129,283,886", "2,742,811", "22,832.06", "-203.04"]]
INDEX_FIELDS = ["日期", "開盤指數", "最高指數", "最低指數", "收盤指數"]
INDEX = [[" 94/01/03", "6,166.39", "6,183.15", "6,129.28", "6,143.12"],
         ["114/01/02", "22,975.71", "23,038.08", "22,713.63", "22,832.06"]]
NOT_OK = {"stat": "很抱歉，沒有符合條件的資料!"}


def reply(fields, rows, title):
    return {"stat": "OK", "date": "20250103", "title": title, "fields": fields, "data": rows}


def turnover_reply(rows=None, fields=None):
    return reply(fields or TURNOVER_FIELDS, TURNOVER if rows is None else rows, "114年01月市場成交資訊")


def index_reply(rows=None, fields=None):
    return reply(fields or INDEX_FIELDS, INDEX if rows is None else rows, "114年01月 發行量加權股價指數歷史資料")


def _client(path, payload):
    return OfflineClient({path: payload})


TURNOVER_PATH, INDEX_PATH = "/afterTrading/FMTQIK", "/TAIEX/MI_5MINS_HIST"


def test_rows_become_typed_days():
    old, new = market_turnover(_client(TURNOVER_PATH, turnover_reply()), "20250103").days
    assert (old.day, new.day) == (date(2005, 1, 3), date(2025, 1, 2))
    assert (new.volume, new.value, new.transactions, new.index, new.change) == (
        6901476303, 379129283886, 2742811, Decimal("22832.06"), Decimal("-203.04"))
    first = taiex_history(_client(INDEX_PATH, index_reply()), "20250103").days[1]
    assert (first.open, first.high, first.low, first.close) == (
        Decimal("22975.71"), Decimal("23038.08"), Decimal("22713.63"), Decimal("22832.06"))


def test_requests_and_no_data():
    seen = []

    def route(params, _body):
        seen.append(dict(params))
        return turnover_reply()

    market_turnover(_client(TURNOVER_PATH, route))
    market_turnover(_client(TURNOVER_PATH, route), "20250103")
    assert seen == [{"response": "json"}, {"response": "json", "date": "20250103"}]
    assert market_turnover(_client(TURNOVER_PATH, NOT_OK), "20990101") is None
    assert taiex_history(_client(INDEX_PATH, index_reply([])), "20250103").days == []


def test_changed_replies_are_an_error():
    with pytest.raises(UpstreamFormatError, match="漲跌點數"):
        market_turnover(_client(TURNOVER_PATH, turnover_reply(fields=TURNOVER_FIELDS[:5] + ["漲跌"])), "20250103")
    with pytest.raises(UpstreamFormatError, match="日期格式"):
        taiex_history(_client(INDEX_PATH, index_reply([["20250102"] + INDEX[1][1:]])), "20250103")
    with pytest.raises(UpstreamFormatError, match="4 欄"):
        taiex_history(_client(INDEX_PATH, index_reply([INDEX[1][:4]])), "20250103")


def test_tools_print_the_same_lines_as_before_the_gateway():
    turnover = register_module_tools(market_turnover_tool, _client(TURNOVER_PATH, turnover_reply()))
    assert turnover["get_market_turnover_history"]("20250103") == (
        "【114年01月市場成交資訊】\n\n"
        " 94/01/03 | 加權指數:6,143.12（3.43）| 成交量:4,227,307,000 | 成交金額:75,449,754,940 | 筆數:637,322\n"
        "114/01/02 | 加權指數:22,832.06（-203.04）| 成交量:6,901,476,303 | 成交金額:379,129,283,886 | 筆數:2,742,811")
    index = register_module_tools(taiex_index_history, _client(INDEX_PATH, index_reply()))
    assert index["get_taiex_index_history"]("20250103") == (
        "【114年01月 發行量加權股價指數歷史資料】\n\n"
        " 94/01/03 | 開:6,166.39 高:6,183.15 低:6,129.28 收:6,143.12\n"
        "114/01/02 | 開:22,975.71 高:23,038.08 低:22,713.63 收:22,832.06")


def test_tools_report_no_data():
    turnover = register_module_tools(market_turnover_tool, _client(TURNOVER_PATH, NOT_OK))
    assert turnover["get_market_turnover_history"]("20990101") == "查無 209901 的市場成交資訊，請確認日期是否有效"
    index = register_module_tools(taiex_index_history, _client(INDEX_PATH, index_reply([])))
    assert index["get_taiex_index_history"]("20250103") == "查無 202501 的加權指數歷史資料"
