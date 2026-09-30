"""utils/market_snapshot.py 與 tools/analytics/screening.py 的單元測試（不打網路）。"""

import pytest

from tests.helpers import register_module_tools
from tests.offline import OfflineClient
from tools.analytics import screening
from utils.market_snapshot import StockSnapshot, market_snapshot

pytestmark = pytest.mark.offline


def _routes(seen):
    def listed_quotes(params, _b):
        seen["listed_quotes_date"] = params.get("date")
        return {"tables": [{"title": "每日收盤行情(全部)", "data": [
            ["2330", "台積電", "1,000", "1", "1", "1", "1", "1", "2,475.00", "<p style ='color:green'>-</p>", "5.00"],
            ["2317", "鴻海", "2,000", "1", "1", "1", "1", "1", "200.00", "<p style ='color:red'>+</p>", "2.00"]]}]}

    def otc_quotes(params, _b):
        seen["otc_quotes_date"] = params.get("date")
        if params.get("type") == "24":
            return {"tables": [{"category": "半導體類", "data": [["6488", "環球晶"]]}]}
        return {"tables": [{"data": [["6488", "環球晶", "945.00", "-3.00", "1", "1", "1", "9,000"]]}]}

    def listed_members(params, _b):
        if params.get("type") == "24":
            return {"tables": [{"title": "115年09月29日 每日收盤行情(半導體業)", "data": [["2330", "台積電"]]}]}
        return listed_quotes(params, _b)

    return {
        "/afterTrading/BWIBBU_d": {"date": "20260929", "data": [
            ["2330", "台積電", "2,475.00", "0.89", 114, "28.69", "9.98", "115/2"],
            ["2317", "鴻海", "200.00", "5.00", 114, "-", "1.20", "115/2"]]},
        "/afterTrading/MI_INDEX": listed_members,
        "/afterTrading/peQryDate": {"date": "20260929", "tables": [{"data": [
            ["6488", "環球晶", "45.87", "7.7", 114, "0.81", "4.67", "115Q2"]]}]},
        "/afterTrading/otc": otc_quotes,
        "/opendata/t187ap03_L": [{"公司代號": "2330", "產業別": "24"}],
        "mopsfin_t187ap03_O": [{"SecuritiesCompanyCode": "6488", "SecuritiesIndustryCode": "24"}],
    }


def test_quotes_are_fetched_for_the_valuation_date():
    seen = {}
    snap, as_of = market_snapshot(OfflineClient(_routes(seen)))
    assert seen == {"listed_quotes_date": "20260929", "otc_quotes_date": "2026/09/29"}
    assert as_of == "上市 20260929、上櫃 20260929"
    assert snap["2330"].change == -5.0 and snap["2317"].change == 2.0 and snap["6488"].change == -3.0
    assert snap["2317"].pe is None  # "-"＝虧損無本益比
    assert snap["2330"].change_pct == pytest.approx(-5 / 2480 * 100)


def test_screener_pe_filter_drops_loss_makers_and_sorts_missing_last():
    fn = register_module_tools(screening, OfflineClient(_routes({})))["get_stock_screener"]
    text = fn(pe_max=50, sort_by="pe")
    assert "2317" not in text and text.index("2330") < text.index("6488")
    by_yield = fn(sort_by="yield")
    assert by_yield.index("2317") < by_yield.index("2330")
    assert "sort_by 只能是" in fn(sort_by="roe") and "market 只能是" in fn(market="us")


def test_screener_same_industry_uses_members_of_both_markets():
    fn = register_module_tools(screening, OfflineClient(_routes({})))["get_stock_screener"]
    text = fn(same_industry_as="2330")
    assert "產業 24 半導體業" in text and "2330" in text and "6488" in text and "2317" not in text


def test_peers_report_median_rank_and_always_show_target():
    fn = register_module_tools(screening, OfflineClient(_routes({})))["get_industry_peers"]
    text = fn("6488", limit=1)
    assert "上市+上櫃共 2 家" in text
    assert "本益比由低到高 2/2" in text and "▶ 6488" in text
    assert "中位數：本益比 37.28" in text


def test_sort_rows_puts_missing_values_last():
    rows = [StockSnapshot("a", "", "上市", pe=None), StockSnapshot("b", "", "上市", pe=5.0)]
    assert [s.code for s in screening.sort_rows(rows, "pe")] == ["b", "a"]
