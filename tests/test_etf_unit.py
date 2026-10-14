"""ETF 工具的離線測試（不打網路）：篩選、合併來源、排序、逐月查詢的參數與格式。

上游介面由 tests/e2e/test_etf_api.py 驗證。
"""

import pytest

from tests.helpers import register_module_tools
from tests.offline import OfflineClient
from tools.etf import daily_nav, info, monthly_stats
from utils.sitca import available_months, query_rows

pytestmark = pytest.mark.offline

INFO_HEADER = ["序號", "會員代碼", "經理公司", "證券代號", "證券簡稱", "基金名稱", "基金成立日期", "分類", "追蹤指數", "是否有發行 配息級別"]
STATEMENT_HEADER = [
    "序號", "類型代號", "證券代號", "證券簡稱", "基金統編", "基金名稱", "類型", "計價幣別", "基金規模(台幣)", "基金規模(原幣)",
    "基金規模市場占有率", "單位淨值(台幣)", "單位淨值(原幣)", "受益權單位數", "自然人受益人數", "法人受益人數", "總受益人數",
    "本月申購總金額(台幣)", "本月申購總金額(原幣)", "本月買回總金額(台幣)", "本月買回總金額(原幣)", "本月定期定額扣款筆數",
    "本月定期定額扣款戶數", "本月定期定額扣款金額(台幣)", "本月定期定額扣款金額(原幣)",
]


def _month_page(months):
    options = "".join(f'<option value="{m}">{m[:4]} 年 {m[4:]} 月</option>' for m in months)
    return f'<select name="ctl00$ContentPlaceHolder1$ddlYM" id="ctl00_ContentPlaceHolder1_ddlYM">{options}</select>'.encode("utf-8")


def _grid(header, rows):
    """SITCA 的結果表放在外層排版表格的儲存格裡。"""
    cells = lambda r, tag: "".join(f"<{tag}>{c}</{tag}>" for c in r)
    body = "".join(f"<tr>{cells(r, 'td')}</tr>" for r in rows)
    total = f"<tr>{cells(['合計'] + ['-'] * (len(header) - 1), 'td')}</tr>"
    grid = f'<table id="ctl00_ContentPlaceHolder1_GridView1"><tr>{cells(header, "th")}</tr>{body}{total}</table>'
    return f'<table id="table2"><tr><td><div>{grid}</div></td></tr></table>'.encode("utf-8")


# ---------- SITCA helpers ----------

def test_sitca_month_list_and_grid_parsing():
    client = OfflineClient({
        "etf_statement.aspx": _month_page(["202608", "202607"]),
        "etf_statement2.aspx": _grid(["序號", "證券代號"], [["1", "0050"]]),
        "etf_info.aspx": b"<html>no select</html>",
        "etf_info2.aspx": b"<html><table><tr><td>changed</td></tr></table></html>",
    })
    assert available_months(client, "etf_statement.aspx") == ["202608", "202607"]
    assert query_rows(client, "etf_statement2.aspx", "202608") == [["序號", "證券代號"], ["1", "0050"]]  # 合計列已去除
    assert query_rows(client, "etf_info2.aspx", "202608") == []
    with pytest.raises(ValueError, match="頁面可能改版"):
        available_months(client, "etf_info.aspx")


# ---------- get_etf_daily_nav ----------

def _all_etf():
    return {"a1": [
        {"msgArray": [
            {"a": "0050", "b": "元大台灣50", "c": 22448000000, "d": 39000000, "e": 113.0, "f": 112.42, "g": 0.52,
             "h": "112.0600", "i": "20261014", "j": "13:31:00", "k": "1"},
            {"a": "00679B", "b": "元大美債20年", "c": "6231192000", "d": "-6500000", "e": "25.05", "f": "25.0181",
             "g": "-0.13", "h": "未結出", "i": "20261014", "j": "17:00:00", "k": "3"},
        ], "refURL": "https://example.invalid/a"},
        {"msgArray": [
            {"a": "00878", "b": "國泰永續高股息", "c": "100", "d": "0", "e": "-", "f": "", "g": "2.5",
             "h": "20.0", "i": "20261013", "j": "17:00:00", "k": "1"},
        ]},
    ]}


def _nav_fn():
    return register_module_tools(daily_nav, OfflineClient({"all_etf.txt": _all_etf()}))["get_etf_daily_nav"]


def test_daily_nav_parses_mixed_types_and_estimates_scale():
    rows = {r["code"]: r for r in daily_nav.parse_all_etf(_all_etf())}
    assert rows["00679B"]["units"] == 6231192000 and rows["00679B"]["change"] == -6500000
    assert rows["00679B"]["prior_nav"] is None
    assert rows["00679B"]["scale"] == pytest.approx(6231192000 * 25.0181)  # 前日淨值未結出時改用預估淨值
    assert rows["00878"]["price"] is None and rows["00878"]["est_nav"] is None


def test_daily_nav_code_lookup_and_rankings():
    fn = _nav_fn()
    text = fn(code="0050, 00679b ,9999")
    assert "資料日期 2026-10-14" in text
    assert "0050 元大台灣50 | 市價 113.00 | 預估淨值 112.4200 | 折溢價 +0.52%" in text
    assert "已發行單位數 22,448,000,000（較前日 +39,000,000）| 規模約 25,155.2 億元" in text
    assert "前日淨值 未結出" in text and "查無：9999" in text

    premium = fn(sort_by="premium").splitlines()
    assert premium[2].startswith("1. 00878") and premium[4].startswith("3. 00679B")
    assert fn(sort_by="discount").splitlines()[2].startswith("1. 00679B")
    assert fn(sort_by="redemption").splitlines()[2].startswith("1. 00679B")
    assert fn(sort_by="scale", limit=1).count("\n1. ") == 1 and "2. " not in fn(sort_by="scale", limit=1)
    assert "sort_by 必須是" in fn(sort_by="volume")
    assert "limit 必須介於" in fn(limit=0)
    assert "查無 ETF 代號 ZZZ" in fn(code="ZZZ")


# ---------- get_etf_info ----------

def _info_routes():
    info_rows = [
        ["1", "A0005", "元大投信", "0050", "元大台灣50", "元大台灣卓越50基金", "20030625", "上市ETF_國內成分證券ETF", "臺灣50指數", "不分級別/分配(半年配)"],
        ["2", "A0005", "元大投信", "00679B", "元大美債20年", "元大美國政府20年期(以上)債券基金", "20170111", "上櫃ETF_債券成分ETF", "ICE美國政府20+年期債券指數", "不分級別/分配(季配)"],
        ["3", "A0022", "復華投信", "-", "-", "復華全球未來50主動式ETF基金", "20260820", "-", "不追蹤指數", "不分級別/分配(年配)"],
    ]
    t187 = [
        {"出表日期": "1151013", "基金代號": "0050", "基金簡稱": "元大台灣50", "基金類型": "國內成分證券指數股票型基金",
         "基金中文名稱": "元大台灣卓越50證券投資信託基金", "標的指數/追蹤指數名稱": "臺灣50指數", "成立日期": "0920625",
         "上市日期": "0920630", "基金經理人": "陳重銓", "總代理人": ""},
        {"出表日期": "1151013", "基金代號": "00635U", "基金簡稱": "期元大S&amp;P黃金", "基金類型": "指數股票型期貨信託基金",
         "基金中文名稱": "元大標普高盛黃金ER指數股票型期貨信託基金", "標的指數/追蹤指數名稱": "標普高盛黃金ER指數", "成立日期": "1040408"},
    ]

    def tpex_list(params, body):
        data = [["00679B", "元大美債20年", "106/01/17"]] if body["type"] == "bond" else []
        return {"stat": "ok", "tables": [{"fields": ["證券代號", "ETF簡稱", "上櫃日期"], "data": data}]}

    def tpex_detail(params, body):
        assert body == {"type": "bond", "code": "00679B", "response": "json"}
        return {"stat": "ok", "tables": [
            {"title": "商品規格", "fields": ["名稱", "證券代號", "管理費", "基金經理公司網站"],
             "data": [["元大美債20年基金", "00679B", "0.12%", '<a href="http://x">http://www.yuantaetfs.com/</a>']]},
            {"title": "申購買回清單PCF", "fields": [""], "data": [["申購買回清單PCF"]]},
        ]}

    return {
        "etf_info.aspx": _month_page(["202608"]),
        "etf_info2.aspx": _grid(INFO_HEADER, info_rows),
        "/opendata/t187ap47_L": t187,
        "ETF/list": tpex_list,
        "ETF/detail": tpex_detail,
    }


def _info_fn():
    return register_module_tools(info, OfflineClient(_info_routes()))["get_etf_info"]


def test_etf_info_list_merges_sitca_with_twse_only_codes():
    fn = _info_fn()
    text = fn()
    assert "共有 3 筆ETF" in text  # 無代號的 SITCA 列不列入；00635U 由 t187ap47_L 補上
    assert "- 0050 元大台灣50 | 元大投信 | 上市ETF_國內成分證券ETF | 臺灣50指數 | 2003-06-25" in text
    assert "- 00635U 期元大S&P黃金 | 指數股票型期貨信託基金 | 標普高盛黃金ER指數 | 2015-04-08" in text
    assert "00679B" in fn(category="債券") and "0050" not in fn(category="債券")
    assert "共有 2 筆" in fn(issuer="元大投信")  # 期信 ETF 沒有 SITCA 經理公司欄
    assert "共有 3 筆" in fn(issuer="元大")  # 但基金名稱仍可比對
    assert "00635U" in fn(keyword="黃金") and "0050" not in fn(keyword="黃金")


def test_etf_info_single_code_combines_sources():
    fn = _info_fn()
    listed = fn(code="0050")
    assert listed.startswith("【0050 元大台灣50 ETF 基本資料】")
    assert "▍投信投顧公會" in listed and "基金成立日期: 2003-06-25" in listed and "配息: 不分級別/分配(半年配)" in listed
    assert "▍證交所基金基本資料" in listed and "上市日期: 2003-06-30" in listed and "基金經理人: 陳重銓" in listed
    assert "出表日期" not in listed and "總代理人" not in listed and "櫃買中心" not in listed

    otc = fn(code="00679b")
    assert "▍櫃買中心商品規格" in otc and "管理費: 0.12%" in otc
    assert "基金經理公司網站: http://www.yuantaetfs.com/" in otc  # HTML 標籤已去除
    assert "申購買回清單PCF" not in otc and "證交所" not in otc
    assert "查無 ETF 代號 9999" in fn(code="9999")


# ---------- get_etf_monthly_stats ----------

def _stat_row(code, fund_id, share_class, scale, holders, subscribe="0", redeem="0"):
    return ["1", "AH11", code, f"簡稱{code}", fund_id, f"基金{fund_id}", share_class, "TWD", scale, "0", "1.5%", "10.0000", "0",
            "1,000,000", holders, "10", holders, subscribe, "0", redeem, "0", "5", "4", "300,000,000", "0"]


def _stats_routes(seen):
    def statement(params, body):
        seen.append((params["txtYM"], params["txtemcode"], params["txtfund"]))
        ym = params["txtYM"]
        if params["txtemcode"] == "0050,":
            return _grid(STATEMENT_HEADER, [_stat_row("0050", "111", "不分級別", "300,000,000,000", "1,000", "20,000,000,000", "5,000,000,000")])
        if params["txtfund"] == "111,":
            rows = {
                "202607": [_stat_row("-", "111", "不分級別", "200,000,000,000", "900")],
                # 多個級別時取與最新月份同級別的那一列
                "202606": [_stat_row("-", "111", "美元級別", "1", "1"), _stat_row("-", "111", "不分級別", "100,000,000,000", "950")],
            }.get(ym, [])
            return _grid(STATEMENT_HEADER, rows)
        if not params["txtemcode"] and not params["txtfund"]:
            return _grid(STATEMENT_HEADER, [
                _stat_row("0050", "111", "不分級別", "300,000,000,000", "1,000", "1,000,000,000", "0"),
                _stat_row("00878", "222", "不分級別", "100,000,000,000", "5,000", "9,000,000,000", "0"),
            ])
        return _grid(STATEMENT_HEADER, [])

    return {"etf_statement.aspx": _month_page(["202608", "202607", "202606", "202605"]), "etf_statement2.aspx": statement}


def test_monthly_stats_history_resolves_fund_id_and_share_class():
    seen = []
    fn = register_module_tools(monthly_stats, OfflineClient(_stats_routes(seen)))["get_etf_monthly_stats"]
    text = fn(code="0050", months=4)
    lines = text.splitlines()
    assert lines[0].startswith("【0050 簡稱0050 每月統計】基金111（共 3 個月") # 202605 無資料即停止
    assert lines[2].startswith("2026-08 | 規模 3,000.0 億（市占 1.5%）")
    assert "受益人數 1,000（自然人 1,000／法人 10），較前月 +100" in lines[2]
    assert "申購 200.0 億／買回 50.0 億（淨 +150.0 億）| 定期定額 5 筆、4 戶、3.0 億" in lines[2]
    assert lines[4].startswith("2026-06 | 規模 1,000.0 億") and "較前月" not in lines[4]
    # 最新月份用代號查，較舊月份改用基金統編查
    assert seen == [("202608", "0050,", ""), ("202607", "", "111,"), ("202606", "", "111,"), ("202605", "", "111,")]


def test_monthly_stats_period_and_validation():
    seen = []
    fn = register_module_tools(monthly_stats, OfflineClient(_stats_routes(seen)))["get_etf_monthly_stats"]
    text = fn(code="0050", months=1, period="202607")
    assert "2026-07 | 規模 2,000.0 億" in text and "2026-08" not in text
    assert "period 必須是 YYYYMM 且介於 202605～202608" in fn(code="0050", period="202001")
    assert "months 必須介於 1～24" in fn(code="0050", months=25)
    assert "查無 ETF 代號 9999" in fn(code="9999")


def test_monthly_stats_ranking_and_column_guard():
    fn = register_module_tools(monthly_stats, OfflineClient(_stats_routes([])))["get_etf_monthly_stats"]
    lines = fn(sort_by="net_flow").splitlines()
    assert lines[0] == "【ETF 淨申購金額排行】2026-08（共 2 檔，列出前 2 檔）"
    assert lines[2].startswith("1. 00878 簡稱00878 | 規模 1,000.0 億")
    assert fn(sort_by="scale").splitlines()[2].startswith("1. 0050")
    assert "sort_by 必須是" in fn(sort_by="nav")
    with pytest.raises(ValueError, match="欄位已變更"):
        monthly_stats.records([["序號", "證券代號"], ["1", "0050"]])
