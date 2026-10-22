"""Contract tests for TDCC 集保股權分散表 and the macro sources (國發會、中央銀行).

The NDC files are fetched from fixed ws.ndc.gov.tw download links copied from
data.gov.tw; if NDC re-points them the request 404s (or returns an HTML page) and these
tests fail, which is the signal to refresh the URLs in sources/ndc/indicators.py.
"""

import pytest

from sources.cbc.exchange_rates import exchange_rates
from sources.ndc.indicators import CYCLE_TABLES, business_cycle, pmi
from sources.tdcc import opendata
from sources.tdcc.levels import TOTAL
from sources.tdcc.qry_stock import StockQuery
from tests.helpers import fetch_bytes_or_skip, gateway_or_skip


class TestTdccShareholdingDistribution:
    """open data 1-5 只透過 sources/tdcc/opendata.py 讀：欄位依表頭名稱取，改名時 gateway 丟 UpstreamFormatError。
    工具寫死持股分級 1–17 的意義。"""

    def test_levels_of_one_code(self):
        dist = gateway_or_skip(opendata.latest_distribution, "2330")
        if dist is None:
            body = fetch_bytes_or_skip(opendata.URL, timeout=60)
            if len(body.decode("utf-8-sig").splitlines()) < 2:
                pytest.skip("集保股權分散表目前沒有資料（上游無資料，非 interface 變更）")
            pytest.fail("2330 不在集保股權分散表中，證券代號欄格式可能已變更")
        assert sorted(h.level for h in dist.levels) == list(range(1, 18)), (
            f"持股分級不再是 1–17: {sorted(h.level for h in dist.levels)}")
        total = next(h for h in dist.levels if h.level == TOTAL)
        assert total.pct == 100, f"第 17 級不再是合計（100%）: {total}"


class TestTdccQueryPage:
    """weeks > 1 走集保查詢頁，只透過 sources/tdcc/qry_stock.py 讀：GET 取 token／日期清單（含 JSESSIONID），每週
    POST 一次，token 逐次更新；結果表依表頭名稱取欄，改名時 gateway 丟 UpstreamFormatError。"""

    def test_page_form_token_and_week_list(self):
        query = gateway_or_skip(StockQuery)  # 缺 token／firDate／日期清單會直接 raise
        # 工具依序取前 N 週當作由新到舊的趨勢
        assert query.dates == sorted(query.dates, reverse=True), f"scaDate 不再由新到舊排列: {query.dates[:5]}"

    def test_week_levels_and_token_chaining(self):
        query = gateway_or_skip(StockQuery)
        week = gateway_or_skip(lambda _client: query.week("2330", query.dates[0]))
        assert week is not None, "2330 最新一週查無資料"
        assert [h.level for h in week.levels] == list(range(1, 16)) + [TOTAL], (
            f"結果表的級距列已變更: {[h.level for h in week.levels]}")
        assert week.total.pct == 100, f"合計列的占比不再是 100%（欄位對應可能已變更）: {week.total}"
        # 第二週用上一個回應發的 token
        assert gateway_or_skip(lambda _client: query.week("2330", query.dates[1])) is not None

    def test_unknown_code_is_no_data(self):
        """查無此資料的字樣是 gateway 區分「沒資料」與錯誤頁的依據."""
        query = gateway_or_skip(StockQuery)
        assert gateway_or_skip(lambda _client: query.week("9999", query.dates[0])) is None


class TestNdcBusinessCycle:
    """國發會兩個檔只透過 sources/ndc/indicators.py 讀：zip 內依檔名找 CSV，每張表首欄是 Date（YYYYMM）；下載內容不是
    zip（連結失效）、找不到檔案或表頭改了，gateway 丟 UpstreamFormatError。"""

    @pytest.mark.parametrize("table", list(CYCLE_TABLES))
    def test_every_zip_table_parses(self, table):
        data = gateway_or_skip(business_cycle, table)
        assert data is not None and data.rows, f"{CYCLE_TABLES[table]} 沒有資料列"

    def test_signal_table_keeps_its_columns(self):
        data = gateway_or_skip(business_cycle, "signal")
        assert {"景氣對策信號綜合分數", "景氣對策信號"} <= set(data.columns), f"燈號欄位已變更: {data.columns}"

    def test_pmi_csv(self):
        data = gateway_or_skip(pmi)
        assert data is not None and data.columns == ("PMI", "NMI"), "PMI CSV 表頭已變更（或連結失效）"


class TestCbcExchangeRates:
    """BP01D01 只透過 sources/cbc/exchange_rates.py 讀：data.structure.Table1 當幣別、data.dataSets 每列是 YYYYMMDD
    加各幣別匯率；結構、列寬或日期格式改了，gateway 丟 UpstreamFormatError。"""

    def test_file_parses(self):
        table = gateway_or_skip(exchange_rates)
        assert table is not None and table.days, "BP01D01 沒有資料"
        assert any("NTD/USD" in c for c in table.currencies), f"新台幣欄位名稱已變更: {table.currencies}"
        assert table.last_updated, "meta.last_updated 已移除"
