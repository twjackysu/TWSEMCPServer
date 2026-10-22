"""
測試 www.twse.com.tw/rwd 五個新增歷史查詢 API（NEW_TOOLS_PLAN.md Tier 1）。
只驗證 tools 中有寫死用到的欄位索引/位置，足以偵測來源 API 結構異動。
"""

import pytest
from sources.twse.bfi82u import institutional_amounts
from sources.twse.fmtqik import market_turnover
from sources.twse.mi_5mins_hist import taiex_history
from sources.twse.mi_index import stock_quotes
from sources.twse.mi_qfiis import foreign_holdings
from tests.helpers import gateway_or_skip

FIXED_DATE = "20250103"  # 固定歷史交易日，確保資料穩定


class TestMarketInstitutionalAmountsGateway:
    """三大法人買賣金額統計 - BFI82U（sources/twse/bfi82u.py）
    get_market_institutional_amounts_history 只透過這個 gateway 讀；欄位依名稱取，改名時 gateway 丟 UpstreamFormatError。
    """

    @pytest.mark.parametrize("period,day", [
        ("day", FIXED_DATE),
        # 週資料用該週第一個交易日查詢；2026-04-06（週一）休市，該週從 04-07 開始
        ("week", "20260407"),
        ("month", "20260915"),
    ])
    def test_fixed_period_parses(self, period, day):
        report = gateway_or_skip(institutional_amounts, period, day)
        assert report is not None and report.amounts, f"{period} {day} 應有資料"
        a = report.amounts[0]
        assert None not in (a.buy, a.sell, a.net), f"數字格式已變更：{a}"

    def test_week_needs_its_first_trading_day(self):
        """工具靠「不是該週第一個交易日就沒有資料」往後一天再查."""
        assert gateway_or_skip(institutional_amounts, "week", "20260406") is None


class TestMiIndexQuotesGateway:
    """全市場每日收盤行情 - MI_INDEX（sources/twse/mi_index.py stock_quotes）
    get_stock_daily_trading、services/market_snapshot（選股、同業比較）都只透過這個 gateway 讀行情表；
    真實回應要能建出 QuoteTable，欄位改名時 gateway 丟 UpstreamFormatError。
    """

    def test_fixed_day_parses_into_typed_quotes(self):
        table = gateway_or_skip(stock_quotes, "ALLBUT0999", FIXED_DATE)
        assert table is not None and table.date == FIXED_DATE, "固定歷史交易日應有每日收盤行情"
        assert table.group.startswith("全部"), f"行情表標題格式已變更: {table.title!r}"
        tsmc = next((q for q in table.quotes if q.code == "2330"), None)
        assert tsmc and tsmc.name == "台積電"
        assert None not in (tsmc.open, tsmc.high, tsmc.low, tsmc.close, tsmc.volume, tsmc.value, tsmc.transactions), (
            f"數字格式已變更：{tsmc}")
        # gateway 從漲跌(+/-) 欄的 HTML 取出正負號
        directions = {q.direction for q in table.quotes}
        assert directions <= {"+", "-", "", "X"} and directions & {"+", "-"}, f"漲跌(+/-) 欄格式已變更: {directions}"


class TestMarketTurnoverGateway:
    """每日市場成交資訊 - FMTQIK（sources/twse/fmtqik.py）
    get_market_turnover_history 只透過這個 gateway 讀；欄位依名稱取、日期解析成 date，改了 gateway 丟 UpstreamFormatError。
    """

    @pytest.mark.parametrize("day", [FIXED_DATE, "20050103"])
    def test_fixed_month_parses(self, day):
        month = gateway_or_skip(market_turnover, day)
        assert month is not None and month.days, f"{day[:6]} 應有資料"
        d = month.days[0]
        assert None not in (d.volume, d.value, d.transactions, d.index, d.change), f"數字格式已變更：{d}"


class TestTaiexHistoryGateway:
    """加權股價指數歷史 - MI_5MINS_HIST（sources/twse/mi_5mins_hist.py）
    get_taiex_index_history 只透過這個 gateway 讀；欄位依名稱取、日期解析成 date，改了 gateway 丟 UpstreamFormatError。
    """

    @pytest.mark.parametrize("day", [FIXED_DATE, "20050103"])
    def test_fixed_month_parses(self, day):
        month = gateway_or_skip(taiex_history, day)
        assert month is not None and month.days, f"{day[:6]} 應有資料"
        d = month.days[0]
        assert None not in (d.open, d.high, d.low, d.close), f"數字格式已變更：{d}"


class TestForeignHoldingsGateway:
    """get_foreign_holdings 只透過 sources/twse/mi_qfiis.py 讀；欄位依名稱取（2009-04-30 以前是「外資」名稱），
    欄位改名會丟 UpstreamFormatError。"""

    @pytest.mark.parametrize("day", [FIXED_DATE, "20050103"])
    def test_fixed_day_parses(self, day):
        report = gateway_or_skip(foreign_holdings, day)
        assert report is not None and report.holdings, f"固定歷史交易日 {day} 應有資料"
        h = report.holdings[0]
        assert None not in (h.issued_shares, h.available_shares, h.held_shares, h.available_pct, h.held_pct,
                            h.limit_pct), f"數字格式已變更：{h}"
