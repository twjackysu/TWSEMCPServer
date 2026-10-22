"""Contract tests for the sources behind the price analytics tools (services/price_series.py):
get_adjusted_price_history, get_technical_indicators and get_otc_exright.

The STOCK_DAY / tradingStock / TWT49U gateways are checked elsewhere (test_history_api.py,
test_otc_history_api.py, test_history_tier3_api.py); these tests check the exDailyQ gateway and
the extra behaviour the analytics rely on.
"""

from datetime import date
from decimal import Decimal

from tests.helpers import fetch_or_skip, gateway_or_skip
from sources.tpex.ex_daily_q import otc_exright_results
from sources.twse.stock_day import STOCK_DAY_URL

FIXED_MONTH = "20250101"


def test_listed_endpoint_rejects_otc_codes():
    """市場判斷：先查上市 STOCK_DAY，查無資料（stat 非 OK）才改查上櫃."""
    resp = fetch_or_skip(STOCK_DAY_URL, params={"response": "json", "stockNo": "6488", "date": FIXED_MONTH})
    assert resp.get("stat") != "OK" and not resp.get("data"), f"STOCK_DAY 開始接受上櫃代號: {resp!r:.200}"


def test_stock_day_title_carries_code_and_name():
    """股票名稱取自 title 的第三段：'114年01月 2330 台積電 各日成交資訊'."""
    resp = fetch_or_skip(STOCK_DAY_URL, params={"response": "json", "stockNo": "2330", "date": FIXED_MONTH})
    parts = str(resp.get("title", "")).split()
    assert len(parts) >= 3 and parts[1] == "2330" and parts[2] == "台積電", f"title 格式已變更: {resp.get('title')}"


class TestOtcExRightGateway:
    """上櫃除權除息計算結果 - bulletin/exDailyQ（sources/tpex/ex_daily_q.py）
    get_otc_exright 與上櫃還原權息都只透過這個 gateway 讀 exDailyQ；真實回應要能建出 OtcExRightReport。
    欄位改名、搬走時 gateway 會丟 UpstreamFormatError，這裡就會失敗。
    """

    @staticmethod
    def _check_columns(results):
        for r in results:
            assert r.kind in ("除權", "除息", "除權息"), f"權/息 欄位異動：{r}"
            # 參考價 ＝ 前收 − 權值 − 息值（四捨五入到分；2008、2015、2025 共 2,098 列誤差都 ≤ 0.005）：
            # 價格、權值、息值三欄沒有被對錯
            assert abs(r.close_before - r.rights - r.dividend - r.reference) <= Decimal("0.01"), r
            assert r.cash_capital_shares is not None and r.cash_capital_price is not None, r

    def test_fixed_year_parses_across_months(self):
        report = gateway_or_skip(otc_exright_results, date(2025, 1, 1), date(2025, 12, 31))
        assert report.stat == "ok" and report.period == "20250101~20251231", report.period
        assert len({(r.day.year, r.day.month) for r in report.results}) > 6, "跨月區間沒有涵蓋多個月份，區間可能被限制"
        self._check_columns(report.results)

    def test_range_before_2016_reads_cash_capital_by_name(self):
        """起點在 2016 年前的區間多一欄「員工紅利轉增資」（在現金增資股數之前）。"""
        report = gateway_or_skip(otc_exright_results, date(2015, 12, 1), date(2015, 12, 31))
        self._check_columns(report.results)
        hengping = next((r for r in report.results if r.code == "8934"), None)
        assert hengping is not None and hengping.cash_capital_shares == 0, f"8934 衡平 104/12/01 沒有現金增資：{hengping}"

    def test_without_dates_returns_today_onward(self):
        report = gateway_or_skip(otc_exright_results)
        assert "~" in report.period, f"不帶日期時不再回傳今天起的區間: {report.period!r}"
