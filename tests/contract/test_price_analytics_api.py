"""Contract tests for the sources behind the price analytics tools (services/price_series.py):
get_adjusted_price_history, get_technical_indicators and get_otc_exright.

The STOCK_DAY / tradingStock / TWT49U gateways are checked elsewhere (test_history_api.py,
test_otc_history_api.py, test_history_tier3_api.py); these tests check the exDailyQ gateway and
the extra behaviour the analytics rely on.
"""

from datetime import date

from tests.helpers import fetch_or_skip, gateway_or_skip
from sources.tpex.ex_daily_q import otc_exright_results
from sources.twse.stock_day import STOCK_DAY_URL

FIXED_MONTH = "20250101"


def test_listed_endpoint_rejects_otc_codes():
    """市場判斷：先查上市 STOCK_DAY，查無資料（stat 非 OK）才改查上櫃."""
    resp = fetch_or_skip(STOCK_DAY_URL, params={"response": "json", "stockNo": "6488", "date": FIXED_MONTH})
    assert resp.get("stat") != "OK" and not resp.get("data"), f"STOCK_DAY 開始接受上櫃代號: {resp!r:.200}"


class TestOtcExRightGateway:
    """上櫃除權除息計算結果 - bulletin/exDailyQ（sources/tpex/ex_daily_q.py）
    get_otc_exright 與上櫃還原權息都只透過這個 gateway 讀 exDailyQ；欄位依名稱取，欄位改名時 gateway 丟
    UpstreamFormatError。起點在 2016 年前的區間多一欄「員工紅利轉增資」，兩種格式各驗一個區間能讀。
    """

    @staticmethod
    def _check_parses(report):
        assert report.results, "固定歷史區間應有資料"
        r = report.results[0]
        assert None not in (r.close_before, r.reference, r.cash_capital_shares), f"數字格式已變更：{r}"

    def test_fixed_year_parses_across_months(self):
        report = gateway_or_skip(otc_exright_results, date(2025, 1, 1), date(2025, 12, 31))
        assert report.stat == "ok" and report.period == "20250101~20251231", report.period
        # 還原權息一次查整段期間：區間不能被截短
        assert len({(r.day.year, r.day.month) for r in report.results}) > 6, "跨月區間沒有涵蓋多個月份，區間可能被限制"
        self._check_parses(report)

    def test_range_before_2016_parses(self):
        self._check_parses(gateway_or_skip(otc_exright_results, date(2015, 12, 1), date(2015, 12, 31)))

    def test_without_dates_returns_today_onward(self):
        report = gateway_or_skip(otc_exright_results)
        assert "~" in report.period, f"不帶日期時不再回傳今天起的區間: {report.period!r}"
