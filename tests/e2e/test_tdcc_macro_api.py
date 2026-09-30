"""Contract tests for TDCC 集保股權分散表 and the macro sources (國發會、中央銀行).

The NDC files are fetched from fixed ws.ndc.gov.tw download links copied from
data.gov.tw; if NDC re-points them the request 404s (or returns an HTML page) and these
tests fail, which is the signal to refresh the URLs in tools/macro/ndc_indicators.py.
"""

import csv
import io
import zipfile

import pytest

from tests.helpers import fetch_or_skip, fetch_bytes_or_skip
from tools.tdcc.shareholding_distribution import TDCC_DISTRIBUTION_URL, LEVELS, parse_distribution_csv
from tools.macro.ndc_indicators import NDC_BUSINESS_CYCLE_ZIP_URL, NDC_PMI_CSV_URL, CYCLE_TABLES, read_zip_csv
from tools.macro.exchange_rates import CBC_FX_URL, CBC_FX_FILE


class TestTdccShareholdingDistribution:
    """get_shareholding_distribution 依欄位位置讀取，並寫死持股分級 1–17 的意義。"""

    def test_header_and_levels(self):
        body = fetch_bytes_or_skip(TDCC_DISTRIBUTION_URL, timeout=60)
        rows = parse_distribution_csv(body)  # 表頭不符會直接 raise
        if not rows:
            pytest.skip("集保股權分散表目前沒有資料（上游無資料，非 interface 變更）")
        tsmc = [r for r in rows if r[1].strip() == "2330"]
        assert tsmc, "2330 不在集保股權分散表中，證券代號欄格式可能已變更"
        assert sorted(r[2].strip() for r in tsmc) == sorted(LEVELS), (
            f"持股分級不再是 1–17: {sorted(r[2] for r in tsmc)}"
        )
        total = next(r for r in tsmc if r[2].strip() == "17")
        assert float(total[5]) == pytest.approx(100.0), f"第 17 級不再是合計（100%）: {total}"


class TestNdcBusinessCycle:
    """get_business_cycle_indicators 以檔名在 zip 內找 CSV，首欄須為 Date（YYYYMM）。"""

    def test_zip_contains_every_table(self):
        body = fetch_bytes_or_skip(NDC_BUSINESS_CYCLE_ZIP_URL, timeout=60)
        assert zipfile.is_zipfile(io.BytesIO(body)), f"下載內容不是 zip（連結可能已失效）: {body[:120]!r}"
        for key, filename in CYCLE_TABLES.items():
            rows = read_zip_csv(body, filename)
            assert rows[0][0].strip() == "Date", f"{filename} 首欄已變更: {rows[0]}"
            assert len(rows) > 12 and len(rows[-1][0].strip()) == 6, f"{filename} 資料列格式已變更: {rows[-1]}"
        signal_header = read_zip_csv(body, CYCLE_TABLES["signal"])[0]
        assert "景氣對策信號" in signal_header, f"燈號欄位已變更: {signal_header}"

    def test_pmi_csv(self):
        body = fetch_bytes_or_skip(NDC_PMI_CSV_URL, timeout=60)
        rows = list(csv.reader(io.StringIO(body.decode("utf-8-sig"))))
        assert rows[0] == ["Date", "PMI", "NMI"], f"PMI CSV 表頭已變更（或連結失效）: {rows[0]}"
        assert len(rows) > 12


class TestCbcExchangeRates:
    """get_exchange_rates 以 data.structure.Table1 當欄名、data.dataSets 首欄為 YYYYMMDD。"""

    def test_structure_matches_datasets(self):
        resp = fetch_or_skip(CBC_FX_URL, params={"FileName": CBC_FX_FILE}, timeout=60)
        data = resp.get("data") or {}
        columns = (data.get("structure") or {}).get("Table1")
        assert isinstance(columns, list) and columns and all("data" in c for c in columns), (
            f"data.structure.Table1 結構已變更: {columns!r:.200}"
        )
        assert any("NTD/USD" in c["data"] for c in columns), "新台幣欄位名稱已變更"
        rows = data.get("dataSets")
        assert isinstance(rows, list) and rows, "data.dataSets 不是非空 list"
        assert all(len(r) == len(columns) + 1 for r in rows[-30:]), "dataSets 列寬與欄位數不符"
        assert len(rows[-1][0]) == 8 and rows[-1][0].isdigit(), f"日期欄格式已變更: {rows[-1][0]}"
        assert "last_updated" in (resp.get("meta") or {}), "meta.last_updated 已移除"
