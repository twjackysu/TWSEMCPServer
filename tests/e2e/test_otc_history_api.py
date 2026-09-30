"""TPEx website endpoints (www.tpex.org.tw/www/zh-tw/...) contract tests.

tools/otc/history.py reads these rows by position, so each test pins the field list (or,
where TPEx repeats identical column names, an arithmetic invariant that only holds for the
column order the tool assumes).
"""

from tests.helpers import fetch_or_skip
from tools.otc.history import TRADING_STOCK_URL, INSTI_DAILY_URL, MARGIN_BALANCE_URL

FIXED_DATE = "2025/01/03"  # 固定歷史交易日
FIXED_OTC_STOCK = "6488"   # 環球晶


def _num(value: str) -> int:
    return int(value.replace(",", "").strip() or 0)


def _first_table(resp) -> dict:
    assert isinstance(resp, dict) and isinstance(resp.get("tables"), list) and resp["tables"], (
        f"回應不再有 tables 陣列: {resp!r:.300}"
    )
    return resp["tables"][0]


class TestOTCStockHistoryAPI:
    """tradingStock：get_otc_stock_history 使用 row[0]~row[8]。"""

    def test_fields_and_row_width(self):
        table = _first_table(fetch_or_skip(
            TRADING_STOCK_URL, params={"code": FIXED_OTC_STOCK, "date": FIXED_DATE, "response": "json"}
        ))
        assert table.get("fields") == [
            "日 期", "成交張數", "成交仟元", "開盤", "最高", "最低", "收盤", "漲跌", "筆數"
        ], f"欄位已變更: {table.get('fields')}"
        rows = table.get("data") or []
        assert rows, "固定歷史月份應有資料"
        assert all(len(r) == 9 for r in rows)


class TestOTCInstitutionalHistoryAPI:
    """insti/dailyTrade：24 欄，其中 7 組「買進/賣出/買賣超」欄名完全相同，只能靠
    加總關係確認 tool 假設的分組順序（外資不含自營商、外資自營商、外資合計、投信、
    自營商自行、自營商避險、自營商合計、三大法人合計）。"""

    def _rows(self):
        table = _first_table(fetch_or_skip(
            INSTI_DAILY_URL,
            params={"type": "Daily", "sect": "EW", "date": FIXED_DATE, "response": "json"},
        ))
        fields = table.get("fields") or []
        assert len(fields) == 24 and fields[:2] == ["代號", "名稱"], f"欄位已變更: {fields}"
        assert fields[-1] == "三大法人買賣超股數合計", f"最末欄已變更: {fields[-1]}"
        rows = table.get("data") or []
        assert rows, "固定歷史交易日應有資料"
        return rows

    def test_column_groups_sum_as_the_tool_assumes(self):
        for r in self._rows():
            assert len(r) == 24, f"列寬不為 24: {r}"
            foreign = _num(r[4]) + _num(r[7])
            assert foreign == _num(r[10]), f"外資合計 != 不含自營商 + 外資自營商: {r}"
            dealer = _num(r[16]) + _num(r[19])
            assert dealer == _num(r[22]), f"自營商合計 != 自行 + 避險: {r}"
            assert _num(r[10]) + _num(r[13]) + _num(r[22]) == _num(r[23]), f"三大法人合計不符: {r}"


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
