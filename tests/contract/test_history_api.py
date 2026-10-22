"""
測試 twse.com.tw/exchangeReport 歷史行情 API。
只驗證 tools 中有寫死用到的欄位索引與格式，足以偵測來源 API 結構異動。
"""

from sources.twse.bwibbu_d import valuation_ratios
from sources.twse.mi_margn import margin_balances
from sources.twse.stock_day import stock_day_month
from sources.twse.stock_day_avg import monthly_closes
from tests.helpers import gateway_or_skip

# Use a fixed historical trading day to ensure data stability
FIXED_DATE = "20250103"
FIXED_STOCK = "2330"  # TSMC


class TestStockDayGateway:
    """個股歷史日K - STOCK_DAY（sources/twse/stock_day.py）
    get_stock_history 與 services/price_series 都只透過這個 gateway 讀 STOCK_DAY；真實回應要能建出
    StockDayMonth。欄位改名、搬走時 gateway 會丟 UpstreamFormatError，這裡就會失敗。
    """

    def test_fixed_month_parses_into_typed_rows(self):
        month = gateway_or_skip(stock_day_month, FIXED_STOCK, 2025, 1)
        assert month is not None, f"{FIXED_STOCK} 2025-01 應有交易資料"
        assert month.name == "台積電", f"title 格式異動（名稱取自 title）？{month.title!r}"
        assert month.rows and all(r.day.year == 2025 and r.day.month == 1 for r in month.rows), "date 不再對應該月"
        first = month.rows[0]
        assert None not in (first.open, first.high, first.low, first.close, first.volume), f"數字格式已變更：{first}"

    def test_unknown_code_is_no_data_not_an_error(self):
        assert gateway_or_skip(stock_day_month, "9999", 2025, 1) is None


class TestBwibbuDailyGateway:
    """全市場估值 - BWIBBU_d（sources/twse/bwibbu_d.py）
    get_stock_valuation_ratios 與 services/market_snapshot 都只透過這個 gateway 讀 BWIBBU_d；欄位改名時
    gateway 丟 UpstreamFormatError。tool 靠回應的 date 擋掉「拿到別天資料卻標成所查日期」。
    """

    def test_fixed_day_parses_and_echoes_its_date(self):
        report = gateway_or_skip(valuation_ratios, FIXED_DATE)
        assert report.found and report.date == FIXED_DATE, f"回應日期 {report.date!r} 與所查日期 {FIXED_DATE} 不符"
        tsmc = next((v for v in report.valuations if v.code == FIXED_STOCK), None)
        assert tsmc is not None and tsmc.name == "台積電", f"{FIXED_DATE} 估值找不到 {FIXED_STOCK}"
        assert None not in (tsmc.close, tsmc.dividend_yield, tsmc.pe, tsmc.pb), f"數字格式已變更：{tsmc}"

    def test_endpoint_actually_honours_date(self):
        """兩個不同日期必須回傳不同資料——舊的 BWIBBU_ALL 端點就是敗在這裡."""
        other_date = "20240315"
        other = gateway_or_skip(valuation_ratios, other_date)
        assert other.date == other_date
        assert other.valuations[0] != gateway_or_skip(valuation_ratios, FIXED_DATE).valuations[0], (
            "不同日期回傳相同資料，端點已不再支援歷史查詢"
        )


class TestMarginBalanceGateway:
    """融資融券 - MI_MARGN（sources/twse/mi_margn.py）
    get_margin_balance 只透過這個 gateway 讀；兩張表依欄位找，個股欄位依 groups 的組名＋欄名取（融資、融券欄名
    相同），欄位或 groups 改了 gateway 丟 UpstreamFormatError。
    """

    def test_fixed_day_parses(self):
        day = gateway_or_skip(margin_balances, FIXED_DATE)
        assert day is not None and day.balances and day.totals, "固定歷史交易日應有資料"
        t = day.totals[0]
        assert None not in (t.buy, t.sell, t.repaid, t.previous, t.today), f"信用交易統計的數字格式已變更：{t}"
        b = next((b for b in day.balances if b.code == FIXED_STOCK), None)
        assert b is not None, f"找不到 {FIXED_STOCK}"
        assert None not in (b.margin.today, b.margin.next_day_limit, b.short.today, b.offset), f"數字格式已變更：{b}"

    def test_non_trading_day_has_no_data(self):
        """指定日期非交易日時，工具靠 gateway 回 None 往前一天找."""
        assert gateway_or_skip(margin_balances, "20250105") is None


class TestStockMonthlyAverageGateway:
    """個股月均價 - STOCK_DAY_AVG（sources/twse/stock_day_avg.py）
    get_stock_monthly_average 只透過這個 gateway 讀；欄位改名、日期格式改變、末列標籤不再是「月平均收盤價」時，
    gateway 丟 UpstreamFormatError。
    """

    def test_fixed_month_parses(self):
        month = gateway_or_skip(monthly_closes, FIXED_STOCK, FIXED_DATE)
        assert month is not None and month.closes, f"{FIXED_STOCK} 2025-01 應有收盤價"
        assert month.average is not None, "末列月平均收盤價的數字格式已變更"
        assert None not in [c.close for c in month.closes], f"收盤價格式已變更：{month.closes[:3]}"

    def test_unknown_code_is_no_data_not_an_error(self):
        assert gateway_or_skip(monthly_closes, "9999", FIXED_DATE) is None
