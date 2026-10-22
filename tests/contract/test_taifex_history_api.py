"""測試 www.taifex.com.tw 期交所資料下載端點（Big5/cp950 CSV，非 openapi.taifex.com.tw）。

tools/taifex/ 的期貨、選擇權行情、三大法人、大額交易人、PCR 工具都讀這些端點（最新交易日與歷史
皆然），全部透過 sources/taifex/ 的 gateway，欄位依 CSV 標題名稱取。這裡只驗證 tool 依賴的介面：
固定日期能經 gateway 解析（標題改了會丟 UpstreamFormatError）、數字仍能解析、工具篩選用的值、
契約篩選方式，以及無資料日回 HTML（工具靠它往前找最新交易日）。
"""

from dataclasses import astuple
from datetime import date

import pytest

from sources.taifex.daily_report import ALL_CONTRACTS, futures_quotes, option_quotes
from sources.taifex.institutional import (
    calls_puts_positions,
    futures_contract_positions,
    institutional_split,
    institutional_totals,
    option_contract_positions,
)
from sources.taifex.large_traders import futures_large_traders, option_large_traders
from sources.taifex.put_call_ratio import put_call_ratios
from sources.taifex.ticks import trades, trading_days
from tests.helpers import fetch_or_skip, gateway_or_skip, records_or_skip
from utils.taifex import SSF_LISTS_URL, TAIFEX_HEADERS


class TestFuturesDailyGateway:
    """get_daily_futures_market_report 只透過 sources/taifex/daily_report.py 讀 futDataDown；欄位依 CSV 標題取，
    標題改了 gateway 丟 UpstreamFormatError。最新交易日往回找時，靠交易時段的「一般」判斷那天是否完整。"""

    def test_fixed_days_parse(self):
        quotes = gateway_or_skip(futures_quotes, "TX", date(2026, 7, 1), date(2026, 7, 3))
        assert quotes, "固定歷史區間應有資料"
        q = next((q for q in quotes if q.session == "一般" and "/" not in q.month), None)
        assert q is not None, "交易時段不再有「一般」，最新交易日判斷需要調整"
        assert None not in (q.open, q.close, q.volume, q.settlement, q.open_interest), f"數字格式已變更：{q}"


class TestOptionsDailyGateway:
    """get_daily_options_market_report 只透過 sources/taifex/daily_report.py 讀 optDataDown（標題列尾端多一個逗號，
    共用的 decode_and_parse_csv 容忍）；欄位依 CSV 標題取。工具以「買權」「賣權」篩選 call_put。"""

    def test_fixed_day_parses_and_commodity_id_filters_server_side(self):
        quotes = gateway_or_skip(option_quotes, "TXO", date(2026, 6, 1), date(2026, 6, 1))
        assert quotes, "固定歷史交易日應有資料"
        assert {q.contract for q in quotes} == {"TXO"}, "commodity_id 不再在伺服器端篩選"
        assert {q.call_put for q in quotes} <= {"買權", "賣權"}, "買賣權欄的值已變更（工具以此篩選）"
        q = next((q for q in quotes if q.volume), None)
        assert q is not None and None not in (q.strike, q.close, q.settlement), f"數字格式已變更：{q}"


class TestInstitutionalGateways:
    """三大法人五個下載頁（totalTableDateDown、futAndOptDateDown、futContractsDateDown、optContractsDateDown、
    callsAndPutsDateDown）只透過 sources/taifex/institutional.py 讀；欄位依 CSV 標題取，標題改了 gateway 丟
    UpstreamFormatError。期交所只保留約三年，固定日期過了保存期限要往後挪。"""

    DAY = date(2026, 6, 1)

    def test_totals_and_split_parse(self):
        totals = gateway_or_skip(institutional_totals, self.DAY, self.DAY)
        split = gateway_or_skip(institutional_split, self.DAY, self.DAY)
        assert totals and split, "固定歷史交易日應有資料"
        for positions in (totals[0].positions, split[0].futures, split[0].options):
            assert None not in astuple(positions), f"數字格式已變更：{positions}"

    def test_contract_code_filters_server_side(self):
        """工具把代碼（TXF、TXO）交給 commodityId 在伺服器端篩選；中文名稱則比對商品名稱."""
        futures = gateway_or_skip(futures_contract_positions, self.DAY, self.DAY, "TXF")
        assert futures, "固定歷史交易日應有資料"
        assert {r.contract for r in futures} == {"臺股期貨"}, (
            f"commodityId 篩選或商品名稱格式已變更：{sorted({r.contract for r in futures})}")
        assert None not in astuple(futures[0].positions), f"數字格式已變更：{futures[0]}"
        for gateway in (option_contract_positions, calls_puts_positions):
            rows = gateway_or_skip(gateway, self.DAY, self.DAY, "TXO")
            assert rows, "固定歷史交易日應有資料"
            assert len({r.contract for r in rows}) == 1, f"{gateway.__name__} commodityId 不再在伺服器端篩選"
            assert None not in astuple(rows[0].positions), f"數字格式已變更：{rows[0]}"

    def test_calls_puts_values(self):
        rows = gateway_or_skip(calls_puts_positions, self.DAY, self.DAY, "TXO") or []
        assert {r.call_put for r in rows} <= {"CALL", "PUT"}, "買賣權別的值已變更（工具以此篩選）"


class TestLargeTraderGateways:
    """get_large_traders_futures_oi／options_oi 只透過 sources/taifex/large_traders.py 讀 largeTraderFutDown／
    largeTraderOptDown。兩頁都沒有契約篩選，工具在本地以契約代碼過濾，預設 TX／TXO。"""

    DAY = date(2026, 6, 1)

    def test_fixed_day_parses_and_has_the_default_contract(self):
        for gateway, default in ((futures_large_traders, "TX"), (option_large_traders, "TXO")):
            rows = gateway_or_skip(gateway, self.DAY, self.DAY)
            assert rows, "固定歷史交易日應有資料"
            assert default in {r.contract for r in rows}, f"{gateway.__name__} 找不到預設契約 {default}"
            assert {r.trader_type for r in rows} <= {"0", "1"}, "交易人類別的代碼已變更（工具以此標示）"
            r = rows[0]
            assert None not in (r.top5_buy, r.top5_sell, r.top10_buy, r.top10_sell, r.market_oi), f"數字格式已變更：{r}"

    def test_options_month_range_and_call_put_values(self):
        """工具以一個月為上限送出區間查詢；以「買權」「賣權」篩選 call_put."""
        rows = gateway_or_skip(option_large_traders, date(2026, 6, 1), date(2026, 6, 30)) or []
        assert len({r.day for r in rows}) > 1, "一個月區間沒有回傳多個交易日"
        assert {r.call_put for r in rows} <= {"買權", "賣權"}, "買賣權欄位的值已變更（工具以此篩選）"


class TestPutCallRatioGateway:
    """get_put_call_ratio 只透過 sources/taifex/put_call_ratio.py 讀 pcRatioDown."""

    def test_fixed_range_parses(self):
        days = gateway_or_skip(put_call_ratios, date(2026, 6, 1), date(2026, 6, 5))
        assert days, "固定歷史區間應有資料"
        assert None not in astuple(days[0]), f"數字格式已變更：{days[0]}"


class TestDownloadPageBehaviourToolsRelyOn:
    """不是欄位順序，而是工具依賴的端點行為。"""

    def test_commodity_all_lists_every_contract(self):
        """contract 留空時，工具以 commodity_id=all 取得全部契約再列出可用代碼."""
        for gateway in (futures_quotes, option_quotes):
            quotes = gateway_or_skip(gateway, ALL_CONTRACTS, date(2026, 6, 1), date(2026, 6, 1)) or []
            contracts = {q.contract for q in quotes}
            assert len(contracts) > 1, f"{gateway.__name__} commodity_id=all 不再回傳全部契約: {sorted(contracts)[:10]}"

    def test_non_trading_day_returns_html_not_csv(self):
        """不帶日期時，工具從今天往前逐日查詢，靠「無資料日回 HTML 頁」（gateway 回 None）判斷該日沒有資料."""
        sunday = date(2026, 9, 27)
        assert gateway_or_skip(institutional_totals, sunday, sunday) is None, "非交易日不再回 HTML 頁，最新交易日判斷需要調整"


class TestFuturesTickDownloadAPI:
    """get_futures_intraday 只透過 sources/taifex/ticks.py 讀：下載頁列出最近 30 個交易日的 DailydownloadCSV zip，
    zip 內一個 cp950 CSV，欄位依表頭名稱取；連結不見、表頭改名或時間／價格／數量讀不出來，gateway 丟 UpstreamFormatError."""

    def test_page_lists_zips_and_trades_parse(self):
        days = gateway_or_skip(trading_days)
        ticks = gateway_or_skip(trades, days[0], "TX")
        if not ticks:
            pytest.skip(f"{days[0]} 的檔案沒有 TX 成交（上游無資料，非 interface 變更）")
        assert all(0 <= t.time <= 235959 for t in ticks), "成交時間不再是 HHMMSS"  # contract-ok: intraday 依 HHMMSS 解析成交時間


class TestStockFuturesListAPI:
    """get_daily_futures_market_report／get_futures_intraday 用 openapi SSFLists 把股票代號換成股票期貨契約."""

    def test_hardcoded_fields_exist(self):
        rows = records_or_skip(fetch_or_skip(SSF_LISTS_URL, headers=TAIFEX_HEADERS, timeout=60), "SSFLists")
        missing = [f for f in ("Contract", "StockCode", "StockName") if f not in rows[0]]
        assert not missing, f"SSFLists 欄位已變更，缺少 {missing}"
