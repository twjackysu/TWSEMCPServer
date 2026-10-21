"""sources/twse/twt49u.py 的單元測試（不打網路）。

上游真實格式由 tests/contract/test_history_tier3_api.py 驗證。
"""

from datetime import date
from decimal import Decimal

import pytest

from sources.twse.twt49u import exright_results
from tests.offline import OfflineClient
from utils.errors import UpstreamFormatError

pytestmark = pytest.mark.offline

FIELDS = ["資料日期", "股票代號", "股票名稱", "除權息前收盤價", "除權息參考價", "權值+息值", "權/息", "漲停價格", "跌停價格",
          "開盤競價基準", "減除股利參考價", "詳細資料", "最近一次申報資料 季別/日期", "最近一次申報每股 (單位)淨值",
          "最近一次申報每股 (單位)盈餘"]
ROWS = [
    ["115年06月11日", "2330", "台積電", "2,255.00", "2,248.99", "6.000035", "息", "2,470.00", "2,025.00", "2,250.00",
     "2,248.99", "", "115/1Q", "248.05", "49.33"],
    ["115年01月22日", "0056", "元大高股息", "38.21", "37.34", "0.866000", "息", "41.07", "33.61", "37.34", "37.34",
     "", "", "58.69", "N/A"],
]
REPLY = {"stat": "OK", "fields": FIELDS, "data": ROWS}
START, END = date(2026, 1, 1), date(2026, 9, 30)


def _client(reply):
    return OfflineClient({"/exRight/TWT49U": reply})


def test_rows_are_typed():
    report = exright_results(_client(REPLY), START, END)
    assert report.found
    tsmc, etf = report.results
    assert (tsmc.day, tsmc.code, tsmc.name, tsmc.kind) == (date(2026, 6, 11), "2330", "台積電", "息")
    assert str(tsmc.close_before) == "2255.00" and tsmc.reference == Decimal("2248.99")
    assert str(tsmc.rights_and_dividend) == "6.000035"
    assert (tsmc.limit_up, tsmc.limit_down, tsmc.opening_reference, tsmc.ex_dividend_reference) == (
        Decimal("2470.00"), Decimal("2025.00"), Decimal("2250.00"), Decimal("2248.99"))
    assert (tsmc.nav_per_share, tsmc.eps) == ("248.05", "49.33")
    assert (etf.nav_per_share, etf.eps) == ("58.69", "N/A")  # 原樣保留：N/A（不適用）與空白（未申報）意思不同


def test_columns_are_found_by_name():
    order = list(reversed(range(len(FIELDS))))
    shuffled = {"stat": "OK", "fields": [FIELDS[i] for i in order], "data": [[r[i] for i in order] for r in ROWS]}
    assert exright_results(_client(shuffled), START, END) == exright_results(_client(REPLY), START, END)


def test_renamed_column_is_an_error():
    with pytest.raises(UpstreamFormatError, match="除權息參考價"):
        exright_results(_client({**REPLY, "fields": [f if f != "除權息參考價" else "參考價" for f in FIELDS]}), START, END)


def test_unparseable_date_is_an_error():
    with pytest.raises(UpstreamFormatError, match="2026-06-11"):
        exright_results(_client({**REPLY, "data": [["2026-06-11"] + ROWS[0][1:]]}), START, END)


@pytest.mark.parametrize("stat", ["很抱歉，沒有符合條件的資料!", "開始日期大於結束日期，請重新查詢!"])
def test_nothing_to_report_keeps_twse_reason(stat):
    report = exright_results(_client({"stat": stat}), START, END)
    assert (report.found, report.stat, report.results) == (False, stat, [])


def test_request_params():
    seen = []

    def route(params, _body):
        seen.append(dict(params))
        return REPLY

    exright_results(_client(route), START, END)
    assert seen == [{"startDate": "20260101", "endDate": "20260930", "response": "json"}]
