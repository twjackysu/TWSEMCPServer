"""
測試 www.twse.com.tw/rwd 五個新增歷史查詢 API（NEW_TOOLS_PLAN.md Tier 2 TWSE 半）。
只驗證 tools 中有寫死用到的欄位索引/位置，足以偵測來源 API 結構異動。
"""

import pytest

from sources.twse.bfiauu import BFIAUU_URL, block_trades
from sources.twse.fmnptk import yearly_trading
from sources.twse.fmsrfk import monthly_trading
from sources.twse.twt93u import TWT93U_URL, short_sale_lending_balances
from sources.twse.twtasu import TWTASU_URL, short_lending_sales
from tests.helpers import fetch_or_skip, gateway_or_skip
from utils.constants import SUMMARY_ROW_LABELS

FIXED_DATE = "20250103"  # 固定歷史交易日，確保資料穩定
FIXED_STOCK = "2330"     # 台積電


class TestMonthlyTradingGateway:
    """個股月成交資訊 - FMSRFK（sources/twse/fmsrfk.py）
    get_stock_monthly_trading 只透過這個 gateway 讀；欄位依名稱取，改名時 gateway 丟 UpstreamFormatError。
    """

    def test_fixed_year_parses(self):
        year = gateway_or_skip(monthly_trading, FIXED_STOCK, FIXED_DATE)
        assert year is not None and year.months, f"{FIXED_STOCK} 2025 應有逐月資料"
        m = year.months[0]
        assert None not in (m.high, m.low, m.average, m.transactions, m.value, m.volume, m.turnover), f"數字格式已變更：{m}"

    def test_unknown_code_is_no_data_not_an_error(self):
        assert gateway_or_skip(monthly_trading, "9999", FIXED_DATE) is None


class TestYearlyTradingGateway:
    """個股歷年成交資訊 - FMNPTK（sources/twse/fmnptk.py）
    get_stock_yearly_trading 只透過這個 gateway 讀；年度表依「年度」欄找，兩個「日期」各依前一欄（最高價、最低價）
    命名，欄位改名或日期不再緊接在價格後面時 gateway 丟 UpstreamFormatError。
    """

    def test_fixed_date_parses(self):
        years = gateway_or_skip(yearly_trading, FIXED_STOCK, FIXED_DATE)
        assert years, f"{FIXED_STOCK} 應有歷年資料"
        y = years[0]
        assert None not in (y.volume, y.value, y.transactions, y.high, y.low, y.average_close), f"數字格式已變更：{y}"
        assert y.high_date and y.low_date, f"最高、最低價日期欄已變更：{y}"

    def test_unknown_code_is_no_data_not_an_error(self):
        assert gateway_or_skip(yearly_trading, "9999", FIXED_DATE) is None


class TestBlockTradesGateway:
    """鉅額交易日成交資訊 - BFIAUU（sources/twse/bfiauu.py）
    get_block_trades_detail 只透過這個 gateway 讀；欄位依名稱取，欄位改名時 gateway 丟 UpstreamFormatError。
    2011-12-16 以前多一欄「交割期別」，兩種格式各驗一天能讀。
    """

    @pytest.mark.parametrize("day", [FIXED_DATE, "20100104"])
    def test_fixed_day_parses(self, day):
        trades = gateway_or_skip(block_trades, day)
        assert trades is not None and trades.trades, f"{day} 應有鉅額交易"
        t = trades.trades[0]
        assert None not in (t.price, t.volume, t.value), f"數字格式已變更：{t}"

    def test_last_row_is_the_total(self):
        """gateway 以證券代號欄的「總計」濾掉末列；標籤改了，總計就會被當成一筆鉅額交易."""
        result = fetch_or_skip(BFIAUU_URL, params={"response": "json", "date": FIXED_DATE})
        assert result["data"][-1][0].strip() in SUMMARY_ROW_LABELS, f"末列不再是彙總列: {result['data'][-1]}"


class TestShortSaleLendingGateway:
    """信用額度總量管制餘額表 - TWT93U（sources/twse/twt93u.py）
    get_short_sale_lending_balance_history 只透過這個 gateway 讀；欄位依 groups 的組名＋欄名取，groups 或欄位
    改了 gateway 丟 UpstreamFormatError。2012-03-16 以前借券是另一組欄位，兩種格式各驗一天能讀。
    """

    @pytest.mark.parametrize("day", [FIXED_DATE, "20100104"])
    def test_fixed_day_parses(self, day):
        balances = gateway_or_skip(short_sale_lending_balances, day)
        assert balances is not None and balances.rows, f"{day} 應有資料"
        r = balances.rows[0]
        assert None not in (r.short.previous, r.short.today, r.lending.previous, r.lending.today), f"數字格式已變更：{r}"

    def test_last_row_is_the_total(self):
        """gateway 以名稱欄的「合計」濾掉末列；標籤改了，合計就會被當成一支股票."""
        result = fetch_or_skip(TWT93U_URL, params={"response": "json", "date": FIXED_DATE, "selectType": "ALL"})
        assert result["data"][-1][1].strip() in SUMMARY_ROW_LABELS, f"末列不再是彙總列: {result['data'][-1]}"


class TestShortLendingSalesGateway:
    """當日融券賣出與借券賣出成交量值 - TWTASU（sources/twse/twtasu.py）
    get_short_sale_lending_trades_history 只透過這個 gateway 讀；欄位依 groups 的組名＋欄名取，groups 或欄位
    改了 gateway 丟 UpstreamFormatError。證券名稱欄是「代號 名稱」，gateway 以空白拆開。
    """

    def test_fixed_day_parses(self):
        day = gateway_or_skip(short_lending_sales, FIXED_DATE)
        assert day is not None and day.sales, "固定歷史交易日應有資料"
        s = next((s for s in day.sales if s.code == FIXED_STOCK), None)
        assert s is not None and s.name, f"找不到 {FIXED_STOCK}，證券名稱欄的「代號 名稱」格式可能已變更"
        assert None not in (s.short_volume, s.short_value, s.lending_volume, s.lending_value), f"數字格式已變更：{s}"

    def test_last_row_is_the_total(self):
        """gateway 以證券名稱欄拆出的第一段「合計」濾掉末列；標籤改了，合計就會被當成一支股票."""
        result = fetch_or_skip(TWTASU_URL, params={"response": "json", "date": FIXED_DATE})
        assert result["data"][-1][0].split(None, 1)[0] in SUMMARY_ROW_LABELS, f"末列不再是彙總列: {result['data'][-1]}"
