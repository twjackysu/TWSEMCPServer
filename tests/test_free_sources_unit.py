"""上櫃歷史、證交所除權息/當沖/指數、集保股權分散、國發會與央行工具的單元測試（不打網路）。

上游欄位結構由 tests/e2e/test_otc_history_api.py、test_history_tier3_api.py、
test_tdcc_macro_api.py 驗證；這裡只測篩選、欄位對應、彙總計算與參數處理。
"""

import io
import zipfile

import pytest

from tests.helpers import register_module_tools
from tests.offline import OfflineClient
from tools.history import exright_day_trading_indices as twse_extra
from tools.macro import exchange_rates, ndc_indicators
from tools.otc import history as otc_history
from tools.tdcc import shareholding_distribution as tdcc

pytestmark = pytest.mark.offline


# ---------- TPEx history ----------

def _insti_row(code, name):
    # 外資不含自營商 超=100、外資自營商 超=20、外資合計 超=120、投信 超=-30、
    # 自營自行 超=5、自營避險 超=-7、自營合計 超=-2、三大法人=88
    return [code, name, "0", "0", "100", "0", "0", "20", "0", "0", "120", "0", "0", "-30",
            "0", "0", "5", "0", "0", "-7", "0", "0", "-2", "88"]


def test_otc_institutional_maps_column_groups():
    client = OfflineClient({"/insti/dailyTrade": {"tables": [{"data": [
        _insti_row("6488", "環球晶"), _insti_row("3105", "穩懋"),
    ]}]}})
    fn = register_module_tools(otc_history, client)["get_otc_institutional_history"]
    text = fn("20260803", stock_no="6488")
    assert "共有 1 筆" in text and "3105" not in text
    assert "外資:120（不含自營商 100，外資自營商 20）" in text
    assert "投信:-30" in text and "自營商:-2（自行 5，避險 -7）" in text and "三大法人合計:88" in text


def test_otc_history_sends_slash_date_and_rejects_bad_dates():
    seen = {}

    def route(params, _body):
        seen.update(params)
        return {"name": "環球晶", "tables": [{"data": [
            ["115/08/03", "15,388", "13,694,380", "870.00", "930.00", "843.00", "866.00", "11.00", "23,455"],
        ]}]}

    tools = register_module_tools(otc_history, OfflineClient({"/afterTrading/tradingStock": route}))
    text = tools["get_otc_stock_history"]("6488", "20260801")
    assert seen["date"] == "2026/08/01"
    assert "開:870.00 高:930.00 低:843.00 收:866.00" in text
    assert "日期格式錯誤" in tools["get_otc_stock_history"]("6488", "2026-08-01")
    assert "日期格式錯誤" in tools["get_otc_margin_balance_history"]("20261301")


def test_otc_empty_day_is_reported_as_non_trading_day():
    client = OfflineClient({"/insti/dailyTrade": {"tables": [{"data": []}]}})
    fn = register_module_tools(otc_history, client)["get_otc_institutional_history"]
    assert "請確認該日期為交易日" in fn("20260801")


def _margin_row(code, name):
    return [code, name, "10", "1", "2", "0", "9", "0", "0.5", "100", "3", "1", "0", "0", "4", "0", "0.1", "100", "0", ""]


def test_otc_margin_summary_only_without_filters():
    payload = {"tables": [{
        "data": [_margin_row("6488", "環球晶"), _margin_row("3105", "穩懋")],
        "summary": [["", "合計(張)", "", "", "", "", "999", "", "", "", "", "", "", "", "88", "", "", "", "", ""]],
    }]}
    fn = register_module_tools(otc_history, OfflineClient({"/margin/balance": payload}))["get_otc_margin_balance_history"]
    assert "全市場合計: 合計(張) 資餘額999 券餘額88" in fn("20260803")
    filtered = fn("20260803", stock_no="6488")
    assert "全市場合計" not in filtered and "融資: 前日10 買1 賣2 現償0 餘額9" in filtered


# ---------- TWSE ex-rights / day trading / indices ----------

def test_day_trading_prepends_market_summary_and_flags_suspension():
    payload = {"stat": "OK", "tables": [
        {"data": [["2,686,586,000", "23.51", "311", "35.14", "312", "35.29"]]},
        {"data": [["2330", "台積電", "", "6,942,000", "16", "15"], ["00400A", "主動國泰", "Y", "1", "2", "3"]]},
    ]}
    fn = register_module_tools(twse_extra, OfflineClient({"/dayTrading/TWTB4U": payload}))["get_day_trading_history"]
    text = fn("20260803")
    assert text.startswith("全市場當沖: 成交股數 2,686,586,000（占 23.51%）")
    assert "00400A 主動國泰（暫停先賣後買）" in text
    assert "2330 台積電 | 當沖股數:6,942,000" in text


def test_day_trading_non_trading_day():
    payload = {"stat": "OK", "tables": [{"data": []}, {"data": []}]}
    fn = register_module_tools(twse_extra, OfflineClient({"/dayTrading/TWTB4U": payload}))["get_day_trading_history"]
    assert "請確認該日期為交易日" in fn("20260801")


def test_indices_keyword_filter_and_sign_from_html():
    payload = {"stat": "OK", "tables": [
        {"title": "價格指數(臺灣證券交易所)", "data": [
            ["發行量加權股價指數", "43,386.41", "<p style ='color:red'>+</p>", "406.36", "0.85", ""],
            ["半導體類指數", "1,491.44", "<p style ='color:green'>-</p>", "3.37", "-0.23", ""],
        ]},
        {"title": None, "data": []},
    ]}
    fn = register_module_tools(twse_extra, OfflineClient({"/afterTrading/MI_INDEX": payload}))["get_twse_indices_by_date"]
    text = fn("20260803", keyword="半導體")
    assert "半導體類指數: 1,491.44 | -3.37 (-0.23%)" in text
    assert "發行量加權" not in text
    assert "查無 20260803 名稱包含「航運」" in fn("20260803", keyword="航運")


def test_exright_filters_by_stock():
    row = ["115年07月01日", "1101", "台泥", "24.05", "23.25", "0.8", "息", "25.55", "20.95", "23.25", "23.25", "", "", "30.86", "0.38"]
    other = list(row)
    other[1] = "2330"
    fn = register_module_tools(twse_extra, OfflineClient({"/exRight/TWT49U": {"stat": "OK", "data": [row, other]}}))[
        "get_exright_results_history"]
    text = fn("20260701", "20260731", stock_no="1101")
    assert "共有 1 筆" in text and "1101 台泥 | 息 | 前收:24.05 參考價:23.25" in text


# ---------- TDCC ----------

def _tdcc_csv(code="2330  "):
    lines = ["資料日期,證券代號,持股分級,人數,股數,占集保庫存數比例%"]
    pct = {"1": "1.00", "2": "2.00", "3": "3.00", "12": "4.00", "13": "5.00", "14": "6.00", "15": "70.00", "17": "100.00"}
    for lv in tdcc.LEVELS:
        lines.append(f"20260924,{code},{lv},10,1000,{pct.get(lv, '0.50')}")
    lines.append("20260924,9999  ,1,1,1,100.00")
    return ("﻿" + "\n".join(lines)).encode("utf-8")


def test_tdcc_filters_padded_code_and_summarizes_big_small_holders():
    fn = register_module_tools(tdcc, OfflineClient({"getOD.ashx?id=1-5": _tdcc_csv()}))["get_shareholding_distribution"]
    text = fn("2330")
    assert "資料日期: 2026-09-24" in text
    assert "千張大戶（1000張以上）: 70.00%" in text
    assert "400張以上大戶: 85.00%" in text
    assert "10張以下散戶: 6.00%" in text
    assert "查無證券代號 0050" in fn("0050")


def test_tdcc_header_change_raises():
    with pytest.raises(ValueError, match="欄位與預期不符"):
        tdcc.parse_distribution_csv("日期,代號\n1,2".encode("utf-8"))


# ---------- NDC ----------

def _ndc_zip():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("景氣指標與燈號.csv", "﻿Date,景氣對策信號綜合分數,景氣對策信號\n202606,40,紅\n202607,41,紅\n202608,,\n")
    return buf.getvalue()


def test_business_cycle_newest_first_with_month_limit():
    fn = register_module_tools(ndc_indicators, OfflineClient({"icon=.zip": _ndc_zip()}))["get_business_cycle_indicators"]
    text = fn(months=2)
    lines = text.splitlines()
    assert lines[1].startswith("2026-08 | 景氣對策信號綜合分數:- | 景氣對策信號:-")
    assert lines[2] == "2026-07 | 景氣對策信號綜合分數:41 | 景氣對策信號:紅"
    assert "2026-06" not in text


def test_business_cycle_table_validation_and_missing_file():
    fn = register_module_tools(ndc_indicators, OfflineClient({"icon=.zip": _ndc_zip()}))["get_business_cycle_indicators"]
    assert "table 只能是" in fn(table="gdp")
    assert "找不到 領先指標構成項目.csv" in fn(table="leading")


# ---------- CBC ----------

CBC_PAYLOAD = {
    "meta": {"last_updated": "2026-08-31"},
    "data": {
        "structure": {"Table1": [{"data": "新台幣NTD/USD"}, {"data": "日圓JPY/USD"}, {"data": "馬克DEM/USD"}]},
        "dataSets": [[f"202608{d:02d}", f"31.{d:03d}", "159.5", "-"] for d in range(1, 31)],
    },
}


def test_exchange_rates_default_window_and_currency_filter():
    fn = register_module_tools(exchange_rates, OfflineClient({"/API/DataAPI/Get": CBC_PAYLOAD}))["get_exchange_rates"]
    text = fn(currency="ntd")
    rows = text.splitlines()[1:]
    assert len(rows) == exchange_rates.DEFAULT_DAYS
    assert rows[-1] == "2026-08-30 | 新台幣NTD/USD:31.030"
    assert "日圓" not in text


def test_exchange_rates_range_drops_placeholder_and_reports_unknown_currency():
    fn = register_module_tools(exchange_rates, OfflineClient({"/API/DataAPI/Get": CBC_PAYLOAD}))["get_exchange_rates"]
    text = fn("20260801", "20260802")
    assert "2026-08-01 | 新台幣NTD/USD:31.001 | 日圓JPY/USD:159.5" in text
    assert "馬克" not in text  # "-" 代表停止報價的幣別
    assert "查無幣別「XYZ」" in fn(currency="XYZ")
    assert "查無 20270101" in fn("20270101")
