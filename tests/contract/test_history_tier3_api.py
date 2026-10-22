"""TWSE rwd contract tests for tools/history/exright_day_trading_indices.py:
TWT49U（除權除息計算結果）、TWTB4U（當日沖銷交易）、MI_INDEX type=IND（指數收盤）。
"""

from datetime import date

from sources.twse.mi_index import MI_INDEX_URL, index_quotes
from sources.twse.twt49u import exright_results
from sources.twse.twtb4u import TWTB4U_URL, day_trading
from tests.helpers import fetch_or_skip, gateway_or_skip

FIXED_DATE = "20250103"  # 固定歷史交易日


class TestExrightResultsHistoryAPI:
    """get_exright_results_history 與還原權息（services/price_series）都經 sources/twse/twt49u.py；
    gateway 依欄位名稱取值，欄位改名會丟 UpstreamFormatError。"""

    def test_fixed_range_parses(self):
        report = gateway_or_skip(exright_results, date(2025, 6, 1), date(2025, 7, 31))
        assert report.found and report.results, f"固定區間查無資料：{report.stat}"
        r = next((r for r in report.results if r.code == "2330"), None)
        assert r is not None, "固定區間找不到 2330"
        assert None not in (r.close_before, r.reference, r.rights_and_dividend, r.limit_up, r.limit_down,
                            r.opening_reference, r.ex_dividend_reference), f"數字格式已變更：{r}"


class TestDayTradingGateway:
    """get_daily_day_trading_targets 只透過 sources/twse/twtb4u.py 讀；兩張表依欄位名稱找、欄位依名稱取，
    欄位改名會丟 UpstreamFormatError。"""

    def test_fixed_day_parses(self):
        report = gateway_or_skip(day_trading, FIXED_DATE)
        assert report is not None and report.published and report.targets, "固定歷史交易日應有資料"
        s = report.summary
        assert s is not None and None not in (s.volume, s.volume_pct, s.buy_value, s.buy_pct, s.sell_value,
                                              s.sell_pct), f"全市場彙總的數字格式已變更：{s}"
        t = report.targets[0]
        assert None not in (t.volume, t.buy_value, t.sell_value), f"個股數字格式已變更：{t}"

    def test_latest_day_parses(self):
        """不帶 date 回最新交易日；晚間公布前只有標的清單（3 欄），公布後才有量值，兩種都要能建出報表."""
        gateway_or_skip(day_trading)


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
