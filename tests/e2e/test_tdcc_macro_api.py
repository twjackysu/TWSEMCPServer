"""Contract tests for TDCC 集保股權分散表 and the macro sources (國發會、中央銀行).

The NDC files are fetched from fixed ws.ndc.gov.tw download links copied from
data.gov.tw; if NDC re-points them the request 404s (or returns an HTML page) and these
tests fail, which is the signal to refresh the URLs in tools/macro/ndc_indicators.py.
"""

import csv
import io
import zipfile

import pytest
import requests

from tests.helpers import fetch_or_skip, fetch_bytes_or_skip
from tools.tdcc.shareholding_distribution import (
    TDCC_DISTRIBUTION_URL, TDCC_QUERY_URL, TDCC_PAGE_HEADERS, LEVELS, _TOKEN_RE,
    parse_distribution_csv, parse_query_page, parse_result_rows,
)
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


class TestTdccQueryPage:
    """weeks > 1 走集保查詢頁：GET 取 token／日期清單（含 JSESSIONID），每週 POST 一次，token 逐次更新。"""

    @staticmethod
    def _post(session, token, first_date, date, code):
        return fetch_bytes_or_skip(
            TDCC_QUERY_URL, method="POST", headers=TDCC_PAGE_HEADERS, timeout=60, session=session,
            data={"SYNCHRONIZER_TOKEN": token, "SYNCHRONIZER_URI": "/portal/zh/smWeb/qryStock",
                  "method": "submit", "firDate": first_date, "scaDate": date,
                  "sqlMethod": "StockNo", "stockNo": code, "stockName": ""},
        ).decode("utf-8", errors="replace")

    def test_page_form_token_and_week_list(self):
        session = requests.Session()
        html = fetch_bytes_or_skip(TDCC_QUERY_URL, headers=TDCC_PAGE_HEADERS, timeout=60, session=session).decode("utf-8")
        token, first_date, dates = parse_query_page(html)  # 缺 token／firDate／日期清單會直接 raise
        assert len(dates) >= 13 and dates == sorted(dates, reverse=True), f"scaDate 清單結構已變更: {dates[:5]}"
        assert first_date == dates[0]

    def test_result_rows_and_token_chaining(self):
        session = requests.Session()
        html = fetch_bytes_or_skip(TDCC_QUERY_URL, headers=TDCC_PAGE_HEADERS, timeout=60, session=session).decode("utf-8")
        token, first_date, dates = parse_query_page(html)
        body = self._post(session, token, first_date, dates[0], "2330")
        levels = parse_result_rows(body)
        assert sorted(levels, key=lambda k: (k == "total", int(k) if k != "total" else 0)) == [str(i) for i in range(1, 16)] + ["total"], (
            f"結果表的級距列已變更: {sorted(levels)}"
        )
        assert sum(r[2] for k, r in levels.items() if k != "total") == pytest.approx(100.0, abs=0.1)
        assert levels["total"][2] == pytest.approx(100.0)
        # 回應帶新 token，下一週的 POST 用它
        nxt = _TOKEN_RE.search(body)
        assert nxt, "回應不再帶下一個 SYNCHRONIZER_TOKEN"
        assert "total" in parse_result_rows(self._post(session, nxt.group(1), first_date, dates[1], "2330"))

    def test_unknown_code_message(self):
        session = requests.Session()
        html = fetch_bytes_or_skip(TDCC_QUERY_URL, headers=TDCC_PAGE_HEADERS, timeout=60, session=session).decode("utf-8")
        token, first_date, dates = parse_query_page(html)
        body = self._post(session, token, first_date, dates[0], "9999")
        assert "查無此資料" in body and "total" not in parse_result_rows(body)


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
