"""TPEx website endpoints (www.tpex.org.tw/www/zh-tw/...) contract tests.

tools/otc/ reads most of these rows by position, so each test pins the field list. insti/dailyTrade,
insti/summary, tradingStock, afterTrading/otc and peQryDate go through their gateways (sources/tpex/),
which check their fields themselves.
"""

import re
from decimal import Decimal

import pytest

from sources.tpex.daily_quotes import otc_daily_quotes
from sources.tpex.insti_daily import INSTI_DAILY_URL, tpex_flows
from sources.tpex.insti_summary import otc_institutional_amounts
from sources.tpex.pe_qry_date import otc_valuation_ratios
from sources.tpex.trading_stock import trading_stock_month
from tests.helpers import fetch_or_skip, gateway_or_skip
from tools.otc.history import MARGIN_BALANCE_URL

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
        assert month.rows and all(r.day.year == 2025 and r.day.month == 1 for r in month.rows)
        for r in month.rows:  # 6488 每個交易日都有成交
            assert None not in (r.open, r.high, r.low, r.close, r.lots, r.value_thousands, r.transactions), r
            assert r.low <= r.open <= r.high and r.low <= r.close <= r.high, r
            # 成交仟元 ÷ 成交張數 ＝ 每股均價（元），應落在當日高低之間：單位（張、仟元）沒變
            assert r.low <= Decimal(r.value_thousands) / r.lots <= r.high, f"成交張數／仟元單位異動？{r}"

    def test_month_before_2025_parses(self):
        """2024-12 以前成交量欄名是「成交仟股」，2025-01 起是「成交張數」（數字相同）。"""
        month = gateway_or_skip(trading_stock_month, FIXED_OTC_STOCK, 2024, 12)
        assert month is not None and month.rows and all(r.lots for r in month.rows), "2024-12 應有交易資料"

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
        assert any(f.code == FIXED_OTC_STOCK for f in day.flows), f"找不到 {FIXED_OTC_STOCK}"


class TestOTCMarginHistoryAPI:
    """margin/balance：get_otc_margin_balance 使用 row[0]~row[19] 與 summary。"""

    EXPECTED_FIELDS = [
        "代號", "名稱", "前資餘額(張)", "資買", "資賣", "現償", "資餘額", "資屬證金", "資使用率(%)", "資限額",
        "前券餘額(張)", "券賣", "券買", "券償", "券餘額", "券屬證金", "券使用率(%)", "券限額", "資券相抵(張)", "備註",
    ]

    def test_fields_and_summary(self):
        table = _first_table(fetch_or_skip(MARGIN_BALANCE_URL, params={"date": FIXED_DATE, "response": "json"}))
        assert table.get("fields") == self.EXPECTED_FIELDS, f"欄位已變更: {table.get('fields')}"
        rows = table.get("data") or []
        assert rows and all(len(r) == 20 for r in rows)
        summary = table.get("summary")
        assert isinstance(summary, list) and summary and len(summary[0]) == 20, (
            f"summary（全市場合計）結構已變更: {summary!r:.200}"
        )


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
    get_otc_daily（帶 date）與 services/market_snapshot 都只透過這個 gateway 讀；真實回應要能建出 OtcQuoteDay。
    2020-04-30 起多了「最後買量」「最後賣量」，最後賣價從第 12 欄移到第 13 欄，所以改版前後各驗一天。"""

    @pytest.mark.parametrize("day", ["20180102", FIXED_DATE.replace("/", "")])
    def test_fixed_day_reads_last_ask_by_name(self, day):
        quotes = gateway_or_skip(otc_daily_quotes, day)
        assert quotes is not None and quotes.date == day, f"{day} 應有資料"
        assert any(q.code == FIXED_OTC_STOCK for q in quotes.quotes), "type=EW 不再包含上櫃股票"
        traded = [q for q in quotes.quotes if q.close and q.last_bid and q.last_ask]
        assert traded, "沒有任何有成交且有最後買賣價的股票"
        for q in traded:
            # 最後買價 ≤ 最後賣價，且賣價在收盤 ±10% 內（這兩天全部成立）：讀到發行股數之類的別欄就會失敗
            assert q.last_bid <= q.last_ask <= q.close * Decimal("1.1") + Decimal("0.01"), q
            assert q.last_ask >= q.close * Decimal("0.9") - Decimal("0.01"), q


class TestOTCValuationGateway:
    """上櫃個股本益比、殖利率、股價淨值比 - afterTrading/peQryDate（sources/tpex/pe_qry_date.py）
    get_otc_valuation 與 services/market_snapshot 都只透過這個 gateway 讀；真實回應要能建出 OtcValuationReport。
    「財報年/季」2025-01-02 起才有，所以改版前後各驗一天。下列條件在 2010–2026 抽樣 7 天全部成立，欄位對錯就會失敗：
    股利年度是查詢年（民國）的前 1–2 年、本益比與淨值比為 N/A 或正數、殖利率與每股股利有值且不為負。"""

    @pytest.mark.parametrize("day,has_fiscal", [("20180102", False), (FIXED_DATE.replace("/", ""), True)])
    def test_fixed_day_values_fit_their_columns(self, day, has_fiscal):
        report = gateway_or_skip(otc_valuation_ratios, day)
        assert report.date == day and report.valuations, f"{day} 應有資料"
        assert any(v.code == FIXED_OTC_STOCK for v in report.valuations)
        roc = int(day[:4]) - 1911
        for v in report.valuations:
            assert int(v.dividend_year) in (roc - 1, roc - 2), v
            assert (v.pe is None or v.pe > 0) and (v.pb is None or v.pb > 0), v
            assert v.dividend_yield is not None and v.dividend_yield >= 0, v
            assert v.dividend_per_share is not None and v.dividend_per_share >= 0, v
            assert bool(re.fullmatch(r"\d{3}Q[1-4]", v.fiscal)) == has_fiscal, v


class TestOTCForeignHoldingsAPI:
    """insti/qfii：get_otc_foreign_holdings 使用 row[0]~row[9]（row[0] 是排行，代號在 row[1]）。"""

    def test_fields_and_ranking(self):
        table = _first_table(fetch_or_skip(
            "https://www.tpex.org.tw/www/zh-tw/insti/qfii",
            params={"date": FIXED_DATE, "response": "json"},
        ))
        fields = table.get("fields") or []
        assert fields[:3] == ["排行", "代號", "名稱"] and "持股比率" in fields[7] and "上限" in fields[8], (
            f"欄位已變更: {fields}"
        )
        rows = table.get("data") or []
        assert rows and rows[0][0] == "1", f"資料不再依持股比率排行: {rows[:1]}"


def test_new_endpoints_return_latest_day_without_date():
    """get_otc_valuation / get_otc_foreign_holdings 不帶 date 時依賴上游回最新交易日."""
    report = gateway_or_skip(otc_valuation_ratios)
    assert len(report.date) == 8 and report.valuations, f"peQryDate 不帶 date 時不再回傳交易日期或資料: {report.date!r}"
    resp = fetch_or_skip("https://www.tpex.org.tw/www/zh-tw/insti/qfii", params={"response": "json"})
    assert len(str(resp.get("date", ""))) == 8, f"insti/qfii 不帶 date 時不再回傳交易日期: {resp!r:.200}"
    assert _first_table(resp).get("data"), "insti/qfii 不帶 date 時沒有資料"


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
    每列 買進 − 賣出 ＝ 買賣超，且 外資及陸資合計、自營商合計、三大法人合計 等於各分項之和（2018–2026 抽樣全部成立），
    欄位或單位名稱對錯就會失敗."""

    @staticmethod
    def _summary(period: str, prod: str = "1"):
        return gateway_or_skip(otc_institutional_amounts, period, prod, FIXED_DATE.replace("/", ""))

    @pytest.mark.parametrize("period", ["Daily", "Weekly", "Monthly"])
    def test_amounts_add_up(self, period):
        summary = self._summary(period)
        assert summary.amounts, f"{period} 固定歷史日期應有資料"
        for a in summary.amounts:
            assert a.buy - a.sell == a.net, a
        net = {a.name: a.net for a in summary.amounts}
        assert net["外資及陸資合計"] == net["外資及陸資(不含自營商)"] + net["外資自營商"], net
        assert net["自營商合計"] == net["自營商(自行買賣)"] + net["自營商(避險)"], net
        assert net["三大法人合計*"] == net["外資及陸資合計"] + net["投信"] + net["自營商合計"], net

    def test_prod_switches_scope(self):
        assert self._summary("Daily", "0").amounts != self._summary("Daily", "1").amounts, "prod 參數不再生效"
