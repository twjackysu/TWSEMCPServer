"""三大法人工具的離線測試：排行方向、範圍篩選、週資料的交易日回退、櫃買彙總的參數對應。

上游介面由 tests/contract/test_twse_institutional_api.py、test_history_tier1_api.py、test_otc_history_api.py 驗證。
"""

import pytest
from fastmcp.exceptions import ToolError

from tests.helpers import register_module_tools
from tests.offline import OfflineClient
from tools.history import institutional
from tools.otc import institutional_summary

pytestmark = pytest.mark.offline


T86_FIELDS = ["證券代號", "證券名稱", "外陸資買進股數(不含外資自營商)", "外陸資賣出股數(不含外資自營商)",
              "外陸資買賣超股數(不含外資自營商)", "外資自營商買進股數", "外資自營商賣出股數", "外資自營商買賣超股數",
              "投信買進股數", "投信賣出股數", "投信買賣超股數", "自營商買賣超股數", "自營商買進股數(自行買賣)",
              "自營商賣出股數(自行買賣)", "自營商買賣超股數(自行買賣)", "自營商買進股數(避險)", "自營商賣出股數(避險)",
              "自營商買賣超股數(避險)", "三大法人買賣超股數"]


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
        return {"stat": "OK", "title": "T86", "fields": T86_FIELDS, "data": T86_ROWS}
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
    with pytest.raises(ToolError, match="category 必須"):
        fn(category="半導體")


def test_otc_summary_maps_period_and_scope():
    seen = []

    def route(params, _body):
        seen.append(params)
        return {"date": "20261019", "tables": [{"subtitle": "週彙總", "fields": ["單位名稱", "買進金額(元)", "賣出金額(元)", "買賣超(元)"],
                                                "data": [["投信", "1", "0", "1"]]}]}

    fn = register_module_tools(institutional_summary, OfflineClient({"/insti/summary": route}))["get_otc_institutional_summary"]
    assert fn(date="20261014", period="week", scope="all").startswith("【週彙總】")
    assert seen[-1] == {"type": "Weekly", "prod": "0", "date": "2026/10/14", "response": "json"}
    fn()
    assert seen[-1] == {"type": "Daily", "prod": "1", "response": "json"}


def test_by_stock_renders_an_older_t86_layout():
    """舊格式的 T86（外資未拆外資自營商、自營商未拆自行／避險）照當時公布的欄位呈現，不再回「查無」."""
    fields = ["證券代號", "證券名稱", "外資買進股數", "外資賣出股數", "外資買賣超股數", "投信買進股數", "投信賣出股數",
              "投信買賣超股數", "自營商買賣超股數", "自營商買進股數", "自營商賣出股數", "三大法人買賣超股數"]
    row = ["2330", "台積電          ", "1,050", "300", "750", "20", "30", "-10", "-5", "10", "15", "735"]
    reply = {"stat": "OK", "title": "103年10月03日 三大法人買賣超日報", "fields": fields, "data": [row]}
    fn = register_module_tools(institutional, OfflineClient({"/fund/T86": reply}))["get_twse_institutional_investors_by_stock"]
    text = fn("2330", "20141003")
    assert "股票名稱：台積電\n" in text
    assert "─── 外資 ───\n  買進：1,050 股\n  賣出：300 股\n  買賣超：750 股" in text and "外資自營商" not in text
    assert "─── 自營商 ───\n  買進：10 股\n  賣出：15 股\n  買賣超：-5 股" in text
    assert text.endswith("═══ 三大法人合計買賣超 ═══\n  735 股")
