"""TPEx website endpoints (www.tpex.org.tw/www/zh-tw/...) contract tests.

tools/otc/ reads every one of these through its gateway (sources/tpex/), which finds the columns by name
and raises UpstreamFormatError when one is gone; the tests call the gateways on fixed past days.
"""

import pytest

from sources.tpex.daily_quotes import otc_daily_quotes
from sources.tpex.insti_daily import INSTI_DAILY_URL, tpex_flows
from sources.tpex.insti_summary import otc_institutional_amounts
from sources.tpex.margin_balance import MARGIN_BALANCE_URL, otc_margin_balances
from sources.tpex.pe_qry_date import otc_valuation_ratios
from sources.tpex.qfii import otc_foreign_holdings
from sources.tpex.trading_stock import trading_stock_month
from tests.helpers import fetch_or_skip, gateway_or_skip

FIXED_DATE = "2025/01/03"  # 固定歷史交易日
FIXED_OTC_STOCK = "6488"   # 環球晶


def _first_table(resp) -> dict:
    assert isinstance(resp, dict) and isinstance(resp.get("tables"), list) and resp["tables"], (
        f"回應不再有 tables 陣列: {resp!r:.300}"
    )
    return resp["tables"][0]


class TestOTCTradingStockGateway:
    """上櫃個股日K - afterTrading/tradingStock（sources/tpex/trading_stock.py）
    get_otc_stock_history 與 services/price_series 都只透過這個 gateway 讀 tradingStock；真實回應要能建出
    TradingStockMonth。欄位改名、搬走時 gateway 會丟 UpstreamFormatError，這裡就會失敗。
    """

    def test_fixed_month_parses(self):
        month = gateway_or_skip(trading_stock_month, FIXED_OTC_STOCK, 2025, 1)
        assert month is not None, f"{FIXED_OTC_STOCK} 2025-01 應有交易資料"
        assert month.name == "環球晶", f"name 欄位異動？{month.name!r}"
        assert month.rows and all(r.day.year == 2025 and r.day.month == 1 for r in month.rows), "date 不再對應該月"
        first = month.rows[0]
        assert None not in (first.open, first.close, first.lots, first.value_thousands), f"數字格式已變更：{first}"

    def test_month_before_2025_parses(self):
        """2024-12 以前成交量欄名是「成交仟股」，2025-01 起是「成交張數」，兩種都要讀得出來。"""
        month = gateway_or_skip(trading_stock_month, FIXED_OTC_STOCK, 2024, 12)
        assert month is not None and month.rows and month.rows[0].lots is not None, "2024-12 應有交易資料"

    def test_listed_or_unknown_code_is_no_data_not_an_error(self):
        assert gateway_or_skip(trading_stock_month, "2330", 2025, 1) is None
        assert gateway_or_skip(trading_stock_month, "9999", 2025, 1) is None


class TestOTCInstitutionalGateway:
    """insti/dailyTrade（sources/tpex/insti_daily.py）：7 組「買進/賣出/買賣超」欄名完全相同，gateway 依順序
    對應外資不含自營商、外資自營商、外資合計、投信、自營商自行、自營商避險、自營商合計，並逐列檢查這個順序
    蘊含的加總；欄位或順序變了就丟 UpstreamFormatError。"""

    def test_fixed_day_parses_with_consistent_sums(self):
        day = gateway_or_skip(tpex_flows, "AL", FIXED_DATE.replace("/", ""))
        assert day is not None and day.date == FIXED_DATE.replace("/", "") and day.flows, "固定歷史交易日應有資料"


class TestOtcMarginGateway:
    """上櫃融資融券餘額 - margin/balance（sources/tpex/margin_balance.py）
    get_otc_margin_balance 只透過這個 gateway 讀；欄位依名稱取（summary 的全市場合計也是），改名時 gateway 丟
    UpstreamFormatError。"""

    def test_fixed_day_parses_with_market_totals(self):
        day = gateway_or_skip(otc_margin_balances, FIXED_DATE.replace("/", ""))
        assert day.balances, "固定歷史交易日應有資料"
        b = next((b for b in day.balances if b.code == FIXED_OTC_STOCK), None)
        assert b is not None, f"找不到 {FIXED_OTC_STOCK}"
        assert None not in (b.margin.balance, b.margin.usage, b.margin.limit, b.short.balance, b.offset), f"數字格式已變更：{b}"
        assert day.totals and day.totals[0].margin_balance is not None, f"summary（全市場合計）已變更：{day.totals}"


def test_omitting_date_returns_latest_day():
    """get_otc_institutional / get_otc_margin_balance 不帶 date 時依賴上游回最新交易日."""
    for url, params in [(INSTI_DAILY_URL, {"type": "Daily", "sect": "EW"}), (MARGIN_BALANCE_URL, {})]:
        resp = fetch_or_skip(url, params={**params, "response": "json"})
        assert isinstance(resp, dict) and len(str(resp.get("date", ""))) == 8, (
            f"{url} 不帶 date 時不再回傳交易日期: {resp!r:.200}"
        )
        _first_table(resp)


class TestOTCDailyQuotesGateway:
    """上櫃每日收盤行情 - afterTrading/otc（sources/tpex/daily_quotes.py）
    get_otc_daily（帶 date）與 services/market_snapshot 都只透過這個 gateway 讀；欄位依名稱取，欄位改名時 gateway
    丟 UpstreamFormatError。2020-04-30 起多了「最後買量」「最後賣量」，兩種格式各驗一天能讀。"""

    @pytest.mark.parametrize("day", ["20180102", FIXED_DATE.replace("/", "")])
    def test_fixed_day_parses(self, day):
        quotes = gateway_or_skip(otc_daily_quotes, day)
        assert quotes is not None and quotes.date == day, f"{day} 應有資料"
        q = next((q for q in quotes.quotes if q.code == FIXED_OTC_STOCK), None)
        assert q is not None, "type=EW 不再包含上櫃股票"
        assert None not in (q.close, q.volume, q.value, q.last_bid, q.last_ask), f"數字格式已變更：{q}"


class TestOTCValuationGateway:
    """上櫃個股本益比、殖利率、股價淨值比 - afterTrading/peQryDate（sources/tpex/pe_qry_date.py）
    get_otc_valuation 與 services/market_snapshot 都只透過這個 gateway 讀；欄位依名稱取，欄位改名時 gateway
    丟 UpstreamFormatError。「財報年/季」2025-01-02 起才有，兩種格式各驗一天能讀。"""

    @pytest.mark.parametrize("day", ["20180102", FIXED_DATE.replace("/", "")])
    def test_fixed_day_parses(self, day):
        report = gateway_or_skip(otc_valuation_ratios, day)
        assert report.date == day and report.valuations, f"{day} 應有資料"
        v = report.valuations[0]
        assert None not in (v.dividend_per_share, v.dividend_yield), f"數字格式已變更：{v}"


class TestOtcForeignHoldingsGateway:
    """上櫃僑外資及陸資持股 - insti/qfii（sources/tpex/qfii.py）
    get_otc_foreign_holdings 只透過這個 gateway 讀；欄位依名稱取，改名時 gateway 丟 UpstreamFormatError。工具標示
    「依持股比率排行」，依賴回應本身照排行排列。"""

    def test_fixed_day_parses_in_rank_order(self):
        day = gateway_or_skip(otc_foreign_holdings, FIXED_DATE.replace("/", ""))
        assert day.holdings, "固定歷史交易日應有資料"
        h = day.holdings[0]
        assert h.rank == 1, f"資料不再依持股比率排行：{h}"
        assert None not in (h.issued_shares, h.held_shares, h.available_pct, h.held_pct, h.limit_pct), (
            f"數字或百分比格式已變更：{h}")


def test_new_endpoints_return_latest_day_without_date():
    """get_otc_valuation / get_otc_foreign_holdings 不帶 date 時依賴上游回最新交易日."""
    report = gateway_or_skip(otc_valuation_ratios)
    assert len(report.date) == 8 and report.valuations, f"peQryDate 不帶 date 時不再回傳交易日期或資料: {report.date!r}"
    holdings = gateway_or_skip(otc_foreign_holdings)
    assert len(holdings.date) == 8, f"insti/qfii 不帶 date 時不再回傳交易日期: {holdings.date!r}"


class TestOTCInstitutionalSectAPI:
    """get_otc_institutional 的 category 對應 sect：EW（預設，不含權證）、EE（etf）；category="stock"
    從 EW 去掉 00 開頭代號，依賴「上櫃 ETF 皆為 00 開頭」."""

    @staticmethod
    def _codes(sect: str) -> set:
        day = gateway_or_skip(tpex_flows, sect, FIXED_DATE.replace("/", ""))
        assert day is not None, f"sect={sect} 固定歷史交易日沒有資料"
        return {f.code for f in day.flows}

    def test_etf_sect_is_exactly_the_00_prefixed_rows(self):
        etf, default = self._codes("EE"), self._codes("EW")
        assert etf and etf == {c for c in default if c.startswith("00")}, (
            "sect=EE 與 EW 中 00 開頭代號不再一致，category=stock 的排除規則需要調整"
        )


class TestOTCInstitutionalSummaryGateway:
    """上櫃三大法人買賣金額彙總 - insti/summary（sources/tpex/insti_summary.py）
    get_otc_institutional_summary 只透過這個 gateway 讀；type 為 Daily／Weekly／Monthly，prod 1＝上櫃股票、0＝上櫃有價證券。
    欄位依名稱取，欄位改名時 gateway 丟 UpstreamFormatError."""

    @staticmethod
    def _summary(period: str, prod: str = "1"):
        return gateway_or_skip(otc_institutional_amounts, period, prod, FIXED_DATE.replace("/", ""))

    @pytest.mark.parametrize("period", ["Daily", "Weekly", "Monthly"])
    def test_each_period_parses(self, period):
        summary = self._summary(period)
        assert summary.amounts, f"{period} 固定歷史日期應有資料"
        a = summary.amounts[0]
        assert None not in (a.buy, a.sell, a.net), f"數字格式已變更：{a}"

    def test_prod_switches_scope(self):
        assert self._summary("Daily", "0").amounts != self._summary("Daily", "1").amounts, "prod 參數不再生效"
