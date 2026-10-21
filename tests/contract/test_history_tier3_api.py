"""TWSE rwd contract tests for tools/history/exright_day_trading_indices.py:
TWT49U（除權除息計算結果）、TWTB4U（當日沖銷交易）、MI_INDEX type=IND（指數收盤）。
"""

from datetime import date

from sources.twse.mi_index import MI_INDEX_URL, index_quotes
from sources.twse.twt49u import exright_results
from tests.helpers import fetch_or_skip, gateway_or_skip
from tools.history.exright_day_trading_indices import TWTB4U_URL

FIXED_DATE = "20250103"  # 固定歷史交易日


class TestExrightResultsHistoryAPI:
    """get_exright_results_history 與還原權息（services/price_series）都經 sources/twse/twt49u.py；
    gateway 依欄位名稱取值，欄位改名會丟 UpstreamFormatError。"""

    def test_fixed_range_parses(self):
        report = gateway_or_skip(exright_results, date(2025, 6, 1), date(2025, 7, 31))
        assert report.found and report.results, f"固定區間查無資料：{report.stat}"
        tsmc = [r for r in report.results if r.code == "2330"]
        assert [r.day for r in tsmc] == [date(2025, 6, 12)], "2330 於 2025-06-12 除息"
        r = tsmc[0]
        assert r.kind == "息" and r.close_before and r.reference and r.rights_and_dividend
        assert None not in (r.limit_up, r.limit_down, r.opening_reference, r.ex_dividend_reference)
        assert r.nav_per_share and r.eps


class TestDayTradingHistoryAPI:
    """get_daily_day_trading_targets 使用 tables[0]（全市場彙總）row[0]~row[5] 與
    tables[1]（個股）row[0]~row[5]。"""

    def test_two_tables_with_expected_fields(self):
        resp = fetch_or_skip(TWTB4U_URL, params={"date": FIXED_DATE, "selectType": "All", "response": "json"})
        assert resp.get("stat") == "OK"
        tables = resp.get("tables") or []
        assert len(tables) >= 2, f"tables 數量已變更: {len(tables)}"
        assert tables[0].get("fields") == [
            "當日沖銷交易總成交股數", "當日沖銷交易總成交股數占市場比重%",
            "當日沖銷交易總買進成交金額", "當日沖銷交易總買進成交金額占市場比重%",
            "當日沖銷交易總賣出成交金額", "當日沖銷交易總賣出成交金額占市場比重%",
        ], f"彙總表欄位已變更: {tables[0].get('fields')}"
        assert tables[1].get("fields") == [
            "證券代號", "證券名稱", "暫停現股賣出後現款買進當沖註記",
            "當日沖銷交易成交股數", "當日沖銷交易買進成交金額", "當日沖銷交易賣出成交金額",
        ], f"個股表欄位已變更: {tables[1].get('fields')}"
        assert tables[0].get("data") and tables[1].get("data"), "固定歷史交易日應有資料"


class TestIndexBoardGateway:
    """get_market_index_info 只透過 sources/twse/mi_index.py index_quotes 讀 type=IND；
    真實回應要能建出 IndexBoard，欄位改名時 gateway 丟 UpstreamFormatError。"""

    def test_fixed_day_parses_into_index_tables(self):
        board = gateway_or_skip(index_quotes, FIXED_DATE)
        assert board is not None and board.date == FIXED_DATE and board.tables, "找不到任何有 title 與 data 的指數表"
        quotes = {q.name: q for t in board.tables for q in t.quotes}
        assert "發行量加權股價指數" in quotes and "半導體類指數" in quotes, "類股指數不再包含於 type=IND"
        taiex = quotes["發行量加權股價指數"]
        assert None not in (taiex.close, taiex.change_points, taiex.change_pct)
        directions = {q.direction for q in quotes.values()}
        assert directions <= {"+", "-", ""} and directions & {"+", "-"}, f"漲跌欄格式已變更: {directions}"


def test_omitting_date_returns_latest_day():
    """get_daily_day_trading_targets / get_market_index_info 不帶 date 時依賴上游回最新交易日."""
    for url, params in [(TWTB4U_URL, {"selectType": "All"}), (MI_INDEX_URL, {"type": "IND"})]:
        resp = fetch_or_skip(url, params={**params, "response": "json"})
        assert resp.get("stat") == "OK" and len(str(resp.get("date", ""))) == 8, (
            f"{url} 不帶 date 時不再回傳最新交易日: {resp!r:.200}"
        )
