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
    fn = register_module_tools(otc_history, client)["get_otc_institutional"]
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
    assert "日期格式錯誤" in tools["get_otc_margin_balance"]("20261301")


def test_otc_defaults_to_latest_day_and_reports_its_date():
    seen = {}

    def route(params, _body):
        seen.update(params)
        return {"date": "20260929", "tables": [{"data": [_insti_row("6488", "環球晶")]}]}

    fn = register_module_tools(otc_history, OfflineClient({"/insti/dailyTrade": route}))["get_otc_institutional"]
    assert "20260929 上櫃三大法人買賣超" in fn()
    assert "date" not in seen


def test_otc_empty_day_is_reported_as_non_trading_day():
    client = OfflineClient({"/insti/dailyTrade": {"tables": [{"data": []}]}})
    fn = register_module_tools(otc_history, client)["get_otc_institutional"]
    assert "請確認該日期為交易日" in fn("20260801")


def _margin_row(code, name):
    return [code, name, "10", "1", "2", "0", "9", "0", "0.5", "100", "3", "1", "0", "0", "4", "0", "0.1", "100", "0", ""]


def test_otc_margin_summary_only_without_filters():
    payload = {"tables": [{
        "data": [_margin_row("6488", "環球晶"), _margin_row("3105", "穩懋")],
        "summary": [["", "合計(張)", "", "", "", "", "999", "", "", "", "", "", "", "", "88", "", "", "", "", ""]],
    }]}
    fn = register_module_tools(otc_history, OfflineClient({"/margin/balance": payload}))["get_otc_margin_balance"]
    assert "全市場合計: 合計(張) 資餘額999 券餘額88" in fn("20260803")
    filtered = fn("20260803", stock_no="6488")
    assert "全市場合計" not in filtered and "融資: 前日10 買1 賣2 現償0 餘額9" in filtered


# ---------- TWSE ex-rights / day trading / indices ----------

def test_day_trading_prepends_market_summary_and_flags_suspension():
    payload = {"stat": "OK", "tables": [
        {"data": [["2,686,586,000", "23.51", "311", "35.14", "312", "35.29"]]},
        {"data": [["2330", "台積電", "", "6,942,000", "16", "15"], ["00400A", "主動國泰", "Y", "1", "2", "3"]]},
    ]}
    fn = register_module_tools(twse_extra, OfflineClient({"/dayTrading/TWTB4U": payload}))["get_daily_day_trading_targets"]
    text = fn("20260803")
    assert text.startswith("全市場當沖: 成交股數 2,686,586,000（占 23.51%）")
    assert "00400A 主動國泰（暫停先賣後買）" in text
    assert "2330 台積電 | 當沖股數:6,942,000" in text


def test_day_trading_before_evening_publication_lists_targets_only():
    """晚間公布前當天只有「代號、名稱、註記」三格，不能因索引越界而查詢失敗."""
    payload = {"stat": "OK", "date": "20260930", "tables": [
        {}, {"data": [["2330", "台積電", ""], ["00400A", "主動國泰", "Y"]]},
    ]}
    fn = register_module_tools(twse_extra, OfflineClient({"/dayTrading/TWTB4U": payload}))["get_daily_day_trading_targets"]
    text = fn()
    assert "當日當沖量值尚未公布" in text
    assert "2330 台積電\n" in text and "00400A 主動國泰（暫停先賣後買）" in text


def test_day_trading_non_trading_day():
    payload = {"stat": "OK", "tables": [{"data": []}, {"data": []}]}
    fn = register_module_tools(twse_extra, OfflineClient({"/dayTrading/TWTB4U": payload}))["get_daily_day_trading_targets"]
    assert "請確認該日期為交易日" in fn("20260801")


def test_indices_keyword_filter_and_sign_from_html():
    payload = {"stat": "OK", "tables": [
        {"title": "價格指數(臺灣證券交易所)", "data": [
            ["發行量加權股價指數", "43,386.41", "<p style ='color:red'>+</p>", "406.36", "0.85", ""],
            ["半導體類指數", "1,491.44", "<p style ='color:green'>-</p>", "3.37", "-0.23", ""],
        ]},
        {"title": None, "data": []},
    ]}
    fn = register_module_tools(twse_extra, OfflineClient({"/afterTrading/MI_INDEX": payload}))["get_market_index_info"]
    text = fn("20260803", category="all", keyword="半導體")
    assert "半導體類指數: 1,491.44 | -3.37 (-0.23%)" in text
    assert "發行量加權" not in text
    assert "名稱包含「航運」" in fn("20260803", category="all", keyword="航運")


INDEX_NAMES = ["發行量加權股價指數", "半導體類指數", "半導體類報酬指數", "臺指反向一倍指數", "臺灣高股息指數"]


@pytest.mark.parametrize("category,expected", [
    ("major", {"發行量加權股價指數", "臺灣高股息指數"}),
    ("sector", {"半導體類指數"}),
    ("return", {"半導體類報酬指數"}),
    ("leverage", {"臺指反向一倍指數"}),
    ("dividend", {"臺灣高股息指數"}),
    ("all", set(INDEX_NAMES)),
])
def test_index_categories(category, expected):
    rows = [[n, "1", "+", "1", "0.1", ""] for n in INDEX_NAMES]
    fn = register_module_tools(twse_extra, OfflineClient({"/afterTrading/MI_INDEX": {"stat": "OK", "tables": [
        {"title": "指數", "data": rows}]}}))["get_market_index_info"]
    text = fn(category=category)
    assert {n for n in INDEX_NAMES if f"{n}:" in text} == expected


def test_index_and_day_trading_default_to_latest_day():
    seen = []

    def route(params, _body):
        seen.append(dict(params))
        return {"stat": "OK", "date": "20260929", "tables": [
            {"title": "t", "data": [["發行量加權股價指數", "1", "+", "1", "0.1", ""]]}, {"data": [["2330", "台積電", "", "1", "2", "3"]]}]}

    client = OfflineClient({"/afterTrading/MI_INDEX": route, "/dayTrading/TWTB4U": route})
    tools = register_module_tools(twse_extra, client)
    assert "【20260929 證交所指數收盤行情" in tools["get_market_index_info"]()
    assert "20260929 上市個股當日沖銷交易" in tools["get_daily_day_trading_targets"]()
    assert all("date" not in p for p in seen)
    assert "category 只能是" in tools["get_market_index_info"](category="tech")


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


def _query_page(token, dates=("20260924", "20260918", "20260911")):
    options = "".join(f'<option value="{d}" >{d}</option>' for d in dates)
    return (
        f'<input type="hidden" name="SYNCHRONIZER_TOKEN" value="{token}" id="SYNCHRONIZER_TOKEN" />'
        f'<input type="hidden" name="firDate" value="{dates[0]}" id="firDate" />'
        f'<select name="scaDate" id="scaDate">{options}</select>'
    )


def _result_page(token, big_pct, big_people, with_token=True):
    # 級距 15（千張大戶）以外各級距人數 10、占比 1.00；序 16 差異數調整應被忽略
    rows = [(str(i), f"L{i}", "10", "1,000", "1.00") for i in range(1, 15)]
    rows.append(("15", "1,000,001以上", f"{big_people:,}", "9,999", f"{big_pct:.2f}"))
    rows.append(("16", "差異數調整", "0", "-5", "0.00"))
    rows.append(("17", "合　計", "1,000", "99,999", "100.00"))
    body = "".join(
        "<tr>" + "".join(f'<td align="right">{c}</td>' for c in r) + "</tr>" for r in rows
    )
    tok = f'<input type="hidden" name="SYNCHRONIZER_TOKEN" value="{token}" />' if with_token else ""
    return f"<html>{tok}<table><tr><th>序</th><th>級距</th><th>人數</th><th>股數</th><th>占比</th></tr>{body}</table></html>"


class _FakeTdccSite:
    """Stateful stand-in for the query page: every POST must carry the token the previous reply issued."""

    def __init__(self, weeks, no_token_after=None, empty_dates=()):
        self.weeks = weeks  # date -> (big_pct, big_people)
        self.no_token_after = no_token_after
        self.empty_dates = set(empty_dates)
        self.issued = None
        self.n = 0
        self.posts = []
        self.gets = 0

    def _new_token(self):
        self.n += 1
        self.issued = f"tok{self.n}"
        return self.issued

    def __call__(self, params, body):
        if not body:  # GET
            self.gets += 1
            return _query_page(self._new_token(), tuple(self.weeks)).encode("utf-8")
        assert body["SYNCHRONIZER_TOKEN"] == self.issued, "token 必須使用上一個回應發的新 token"
        self.posts.append((body["scaDate"], body["stockNo"]))
        if body["stockNo"] != "2330" or body["scaDate"] in self.empty_dates:
            return f'<span>查無此資料</span><input name="SYNCHRONIZER_TOKEN" value="{self._new_token()}" />'.encode("utf-8")
        big_pct, big_people = self.weeks[body["scaDate"]]
        send = self.no_token_after is None or len(self.posts) <= self.no_token_after
        # 不帶新 token 時，回應中不含 token（讓工具重新載入頁面）
        return _result_page(self._new_token() if send else self.issued, big_pct, big_people, with_token=send).encode("utf-8")


_TDCC_WEEKS = {"20260924": (71.0, 45), "20260918": (70.0, 41), "20260911": (69.5, 40)}


def _tdcc_fn(site):
    return register_module_tools(tdcc, OfflineClient({"qryStock": site}))["get_shareholding_distribution"]


def test_tdcc_weekly_trend_chains_tokens_and_shows_week_over_week_change():
    site = _FakeTdccSite(_TDCC_WEEKS)
    text = _tdcc_fn(site)("2330", weeks=3)
    lines = text.splitlines()
    assert "共 3 週" in lines[0]
    assert lines[2].startswith("2026-09-24 | 總人數 1,000 | 千張大戶 71.00%（45 人）")
    assert "較前週: 千張大戶 +1.00pp（+4 人）" in lines[2]
    assert "400張以上 74.00%（75 人）" in lines[2]  # 級距 12–15：3 級各 1.00%／10 人 + 級距 15 的 71.00%／45 人
    assert "10張以下 3.00%（30 人）" in lines[2]
    assert "較前週" not in lines[4]  # 最舊一週沒有可比較的前一週
    assert [d for d, _ in site.posts] == ["20260924", "20260918", "20260911"]


def test_tdcc_weekly_trend_skips_weeks_without_data_and_reloads_page_when_token_missing():
    site = _FakeTdccSite(_TDCC_WEEKS, empty_dates=("20260918",))
    text = _tdcc_fn(site)("2330", weeks=3)
    assert "共 2 週" in text.splitlines()[0] and "2026-09-18" not in text

    site = _FakeTdccSite(_TDCC_WEEKS, no_token_after=1)  # 第 1 次 POST 之後的回應都不帶 token
    text = _tdcc_fn(site)("2330", weeks=3)
    assert "共 3 週" in text.splitlines()[0]
    assert site.gets > 1, "回應沒帶 token 時應重新載入查詢頁取得新 token"


def test_tdcc_weekly_trend_unknown_code_and_cached_weeks():
    fn_site = _FakeTdccSite(_TDCC_WEEKS)
    fn = _tdcc_fn(fn_site)
    assert "查無證券代號 9999" in fn("9999", weeks=3)
    fn("2330", weeks=3)
    posts_after_first = len(fn_site.posts)
    fn("2330", weeks=3)
    assert len(fn_site.posts) == posts_after_first, "已查過的週不應重送 POST"


def test_tdcc_weeks_validation():
    fn = _tdcc_fn(_FakeTdccSite(_TDCC_WEEKS))
    assert "weeks 必須介於 1～13" in fn("2330", weeks=0)
    assert "weeks 必須介於 1～13" in fn("2330", weeks=14)


def test_tdcc_result_rows_ignore_reconciliation_row_and_page_change_raises():
    levels = tdcc.parse_result_rows(_result_page("t", 70.0, 41))
    assert sorted(levels, key=lambda k: (k == "total", int(k) if k != "total" else 0))[-2:] == ["15", "total"]
    assert "16" not in levels and levels["total"] == (1000, 99999, 100.0)
    with pytest.raises(ValueError, match="頁面可能改版"):
        tdcc.parse_query_page("<html>changed</html>")


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


# ---------- TPEx quotes by date / valuation / foreign holdings ----------

from tools.otc import daily_close as otc_daily_close  # noqa: E402
from tools.otc import valuation_holdings as otc_valuation_holdings  # noqa: E402


def _quote_row(code, name):
    return [code, name, "10", "+1", "9", "11", "9", "1,000", "10,000", "5", "10", "1", "10.1", "1", "100", "11", "9"]


def test_otc_daily_by_date_uses_stock_list_then_falls_back_to_all_securities():
    seen = []

    def route(params, _body):
        seen.append(params["type"])
        rows = [_quote_row("6488", "環球晶")]
        if params["type"] == "AL":
            rows.append(_quote_row("713046", "宜特凱基63購02"))
        return {"date": "20260929", "tables": [{"data": rows}]}

    fn = register_module_tools(otc_daily_close, OfflineClient({"/afterTrading/otc": route}))["get_otc_daily"]
    assert "6488 環球晶" in fn("20260929", stock_no="6488") and seen == ["EW"]
    text = fn("20260929", stock_no="713046")
    assert seen == ["EW", "EW", "AL"] and "713046" in text and "含權證" in text


def test_otc_daily_latest_uses_openapi_with_average_price():
    payload = [{"Date": "1150929", "SecuritiesCompanyCode": "6488", "CompanyName": "環球晶", "Close": "945",
                "Change": "-3 ", "Open": "940", "High": "964", "Low": "930", "Average": "946.19",
                "TradingShares": "1", "TransactionAmount": "2", "TransactionNumber": "3"}]
    fn = register_module_tools(otc_daily_close, OfflineClient({"tpex_mainboard_daily_close_quotes": payload}))["get_otc_daily"]
    assert "均價: 946.19" in fn(stock_no="6488") and "漲跌: -3 |" in fn(stock_no="6488")


def test_otc_foreign_holdings_filters_on_the_code_column_not_the_rank():
    rows = [["1", "8455", "大拓-KY", "25", "3", "22", "12%", "87%", "100%", ""],
            ["2", "6488", "環球晶", "50", "10", "40", "20%", "80%", "100%", ""]]
    tools = register_module_tools(otc_valuation_holdings, OfflineClient({"/insti/qfii": {"date": "20260929", "tables": [{"data": rows}]}}))
    text = tools["get_otc_foreign_holdings"](stock_no="6488")
    assert "#2 6488 環球晶 | 外資持股比率:80%" in text and "8455" not in text
    assert "查無符合條件" in tools["get_otc_foreign_holdings"](stock_no="1")


def test_otc_valuation_shows_dividend_year_and_fiscal_quarter():
    rows = [["6488", "環球晶          ", "45.87", "7.7", 114, "0.81", "4.67", "115Q2"]]
    fn = register_module_tools(otc_valuation_holdings, OfflineClient({"/afterTrading/peQryDate": {"date": "20260929", "tables": [{"data": rows}]}}))["get_otc_valuation"]
    assert "6488 環球晶 | 本益比: 45.87 | 殖利率: 0.81%（每股股利 7.7，股利年度 114）| 股價淨值比: 4.67（財報 115Q2）" in fn()
    assert "日期格式錯誤" in fn("2026-09-29")
