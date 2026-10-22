"""services/market_snapshot.py 與 tools/analytics/screening.py 的單元測試（不打網路）。"""

import pytest
from fastmcp.exceptions import ToolError

from tests.helpers import register_module_tools
from tests.offline import OfflineClient
from tools.analytics import screening
from services.market_snapshot import StockSnapshot, data_date_label, market_snapshot

pytestmark = pytest.mark.offline


QUOTE_FIELDS = ["證券代號", "證券名稱", "成交股數", "成交筆數", "成交金額", "開盤價", "最高價", "最低價", "收盤價",
                "漲跌(+/-)", "漲跌價差", "最後揭示買價", "最後揭示買量", "最後揭示賣價", "最後揭示賣量", "本益比"]
BWIBBU_FIELDS = ["證券代號", "證券名稱", "收盤價", "殖利率(%)", "股利年度", "本益比", "股價淨值比", "財報年/季"]
OTC_QUOTE_FIELDS = ["代號", "名稱", "收盤 ", "漲跌", "開盤 ", "最高 ", "最低", "成交股數  ", " 成交金額(元)", " 成交筆數 ",
                    "最後買價", "最後買量<br>(張數)", "最後賣價", "最後賣量<br>(張數)", "發行股數 ", "次日漲停價 ", "次日跌停價"]


def _routes(seen):
    def listed_quotes(params, _b):
        seen["listed_quotes_date"] = params.get("date")
        return {"stat": "OK", "date": params.get("date", ""), "tables": [{"title": "每日收盤行情(全部)", "fields": QUOTE_FIELDS, "data": [
            ["2330", "台積電", "1,000", "1", "1", "1", "1", "1", "2,475.00", "<p style ='color:green'>-</p>", "5.00", "", "", "", "", "28.69"],
            ["2317", "鴻海", "2,000", "1", "1", "1", "1", "1", "200.00", "<p style ='color:red'>+</p>", "2.00", "", "", "", "", ""]]}]}

    def otc_quotes(params, _b):
        seen["otc_quotes_date"] = params.get("date")
        row = ["6488", "環球晶", "945.00", "-3.00", "1", "1", "1", "9,000"] + ["0"] * 9
        if params.get("type") == "24":
            return {"tables": [{"category": "半導體類", "fields": OTC_QUOTE_FIELDS, "data": [row]}]}
        return {"tables": [{"fields": OTC_QUOTE_FIELDS, "data": [row]}]}

    def listed_members(params, _b):
        if params.get("type") == "24":
            return {"stat": "OK", "date": "20260929", "tables": [{"title": "115年09月29日 每日收盤行情(半導體業)", "fields": QUOTE_FIELDS,
                                                             "data": [["2330", "台積電"] + [""] * 14]}]}
        return listed_quotes(params, _b)

    return {
        "/afterTrading/BWIBBU_d": {"stat": "OK", "date": "20260929", "fields": BWIBBU_FIELDS, "data": [
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
    snap, days = market_snapshot(OfflineClient(_routes(seen)))
    assert seen == {"listed_quotes_date": "20260929", "otc_quotes_date": "2026/09/29"}
    assert days == {"上市": "20260929", "上櫃": "20260929"}
    assert data_date_label(days) == "上市 20260929、上櫃 20260929"
    assert snap["2330"].change == -5.0 and snap["2317"].change == 2.0 and snap["6488"].change == -3.0
    assert snap["2317"].pe is None  # "-"＝虧損無本益比
    assert snap["2330"].change_pct == pytest.approx(-5 / 2480 * 100)


def _text(result):
    return result.content[0].text


def test_screener_pe_filter_drops_loss_makers_and_sorts_missing_last():
    fn = register_module_tools(screening, OfflineClient(_routes({})))["get_stock_screener"]
    result = fn(pe_max=50, sort_by="pe")
    text = _text(result)
    assert "2317" not in text and text.index("2330") < text.index("6488")
    data = result.structured_content
    assert [s["code"] for s in data["stocks"]] == ["2330", "6488"] and data["total"] == 2
    assert data["listed_date"] == data["otc_date"] == "2026-09-29"
    assert data["stocks"][0] == {
        "code": "2330", "name": "台積電", "market": "上市", "close": 2475.0, "change": -5.0,
        "change_pct": pytest.approx(-5 / 2480 * 100), "pe": 28.69, "pb": 9.98, "dividend_yield": 0.89,
        "dividend_year": "114", "fiscal": "115/2", "volume": 1000.0}
    by_yield = fn(sort_by="yield")
    assert _text(by_yield).index("2317") < _text(by_yield).index("2330")
    assert [s["code"] for s in by_yield.structured_content["stocks"]] == ["2317", "2330", "6488"]


def test_screener_pages_the_structured_rows_like_the_text():
    fn = register_module_tools(screening, OfflineClient(_routes({})))["get_stock_screener"]
    page = fn(sort_by="yield", limit=1, offset=1)
    assert page.structured_content["total"] == 3 and page.structured_content["offset"] == 1
    assert [s["code"] for s in page.structured_content["stocks"]] == ["2330"]
    assert "2330" in _text(page) and "2317" not in _text(page)
    past_end = fn(offset=5)
    assert past_end.structured_content["stocks"] == [] and "offset=5 已超出範圍" in _text(past_end)
    none = fn(pe_min=1000)
    assert none.structured_content["total"] == 0 and "查無符合條件" in _text(none)


def test_screener_same_industry_uses_members_of_both_markets():
    fn = register_module_tools(screening, OfflineClient(_routes({})))["get_stock_screener"]
    result = fn(same_industry_as="2330")
    text = _text(result)
    assert "產業 24 半導體業" in text and "2330" in text and "6488" in text and "2317" not in text
    assert (result.structured_content["industry"], result.structured_content["industry_name"]) == ("24", "半導體業")


def test_screener_unknown_same_industry_stock_is_an_error():
    fn = register_module_tools(screening, OfflineClient(_routes({})))["get_stock_screener"]
    with pytest.raises(ToolError, match="查無 9999 的產業別"):
        fn(same_industry_as="9999")


def test_peers_report_median_rank_and_always_show_target():
    fn = register_module_tools(screening, OfflineClient(_routes({})))["get_industry_peers"]
    result = fn("6488", limit=1)
    text = _text(result)
    assert "上市+上櫃共 2 家" in text
    assert "本益比由低到高 2/2" in text and "▶ 6488" in text
    assert "中位數：本益比 37.28" in text
    data = result.structured_content
    assert data["peer_count"] == 2 and data["median_pe"] == pytest.approx(37.28)
    assert data["pe_rank"] == {"position": 2, "of": 2} and data["pb_rank"] == {"position": 1, "of": 2}
    assert [s["code"] for s in data["peers"]] == ["2330", "6488"] and data["not_shown"] == 1


def test_peers_of_an_unknown_stock_is_an_error():
    fn = register_module_tools(screening, OfflineClient(_routes({})))["get_industry_peers"]
    with pytest.raises(ToolError, match="查無 9999 的產業別"):
        fn("9999")


def test_sort_rows_puts_missing_values_last():
    rows = [StockSnapshot("a", "", "上市", pe=None), StockSnapshot("b", "", "上市", pe=5.0)]
    assert [s.code for s in screening.sort_rows(rows, "pe")] == ["b", "a"]
