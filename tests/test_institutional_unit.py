"""三大法人工具的離線測試：排行方向、範圍篩選、週資料的交易日回退、櫃買彙總的參數對應。

上游介面由 tests/e2e/test_twse_institutional_api.py、test_history_tier1_api.py、test_otc_history_api.py 驗證。
"""

import pytest

from tests.helpers import register_module_tools
from tests.offline import OfflineClient
from tools.history import institutional, institutional_amounts
from tools.otc import institutional_summary

pytestmark = pytest.mark.offline


def _t86_row(code, foreign, foreign_dealer, trust, dealer, total):
    row = [code, f"名稱{code}"] + ["0"] * 17
    row[4], row[7], row[10], row[11], row[18] = foreign, foreign_dealer, trust, dealer, total
    return row


T86_ROWS = [
    _t86_row("2330", "-500", "0", "100", "0", "-400"),
    _t86_row("2317", "300", "50", "-20", "0", "330"),
    _t86_row("00631L", "10", "0", "0", "-9000", "-8990"),
    _t86_row("1101", "0", "0", "0", "0", "0"),
]


def _summary_fn(seen):
    def route(params, _body):
        seen.append(params)
        return {"stat": "OK", "title": "T86", "data": T86_ROWS}
    return register_module_tools(institutional, OfflineClient({"/fund/T86": route}))["get_twse_institutional_investors_summary"]


def test_summary_ranks_by_investor_and_side():
    seen = []
    fn = _summary_fn(seen)
    buy = fn(sort_by="foreign", side="buy")
    assert buy.index("2317") < buy.index("00631L") and "2330" not in buy  # 外資含外資自營商：350 > 10
    assert "依外資買超排序" in buy and seen[-1] == {"response": "json", "selectType": "ALLBUT0999"}
    sell = fn(side="sell")
    assert sell.index("00631L") < sell.index("2330") and "2317" not in sell
    assert "1101" not in fn()  # 無進出的不列入


def test_summary_category_mapping_and_stock_filter():
    seen = []
    fn = _summary_fn(seen)
    assert "00631L" not in fn(date="20261016", category="stock")
    assert seen[-1] == {"response": "json", "selectType": "ALLBUT0999", "date": "20261016"}
    fn(category="etf")
    fn(category="24")
    assert [p["selectType"] for p in seen[-2:]] == ["0099P", "24"]
    assert "category 必須" in fn(category="半導體")
    assert "side 必須是" in fn(side="up")


def test_amounts_week_falls_forward_to_first_trading_day():
    seen = []

    def route(params, _body):
        seen.append(params.get("weekDate") or params.get("monthDate") or params.get("dayDate"))
        if params["type"] == "week" and params["weekDate"] != "20260407":
            return {"stat": "很抱歉，沒有符合條件的資料!"}
        title = {"week": "04月07日至04月10日", "month": "10月01日至10月19日"}.get(params["type"], "10月19日")
        return {"stat": "OK", "date": "20261019", "title": title, "data": [["合計", "100,000,000", "0", "100,000,000"]]}

    fn = register_module_tools(institutional_amounts, OfflineClient({"/fund/BFI82U": route}))["get_market_institutional_amounts_history"]
    week = fn(date="20260409", period="week")
    assert "04月07日至04月10日" in week and seen == ["20260406", "20260407"]  # 週一休市 → 週二
    assert "合計：買進 1.00 億 | 賣出 0.00 億 | 買賣差額 1.00 億（100,000,000 元）" in week
    seen.clear()
    assert "10月01日至10月19日" in fn(period="month") and seen == [None, "20261019"]  # 先取最新交易日
    assert "period 必須是" in fn(period="year")


def test_otc_summary_maps_period_and_scope():
    seen = []

    def route(params, _body):
        seen.append(params)
        return {"date": "20261019", "tables": [{"subtitle": "週彙總", "data": [["投信", "1", "0", "1"]]}]}

    fn = register_module_tools(institutional_summary, OfflineClient({"/insti/summary": route}))["get_otc_institutional_summary"]
    assert fn(date="20261014", period="week", scope="all").startswith("【週彙總】")
    assert seen[-1] == {"type": "Weekly", "prod": "0", "date": "2026/10/14", "response": "json"}
    fn()
    assert seen[-1] == {"type": "Daily", "prod": "1", "response": "json"}
    assert "scope 必須是" in fn(scope="otc")
