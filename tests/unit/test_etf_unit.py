"""ETF 工具的離線測試（不打網路）：篩選、合併來源、排序、逐月查詢的參數與格式。

上游介面由 tests/contract/test_etf_api.py 驗證。
"""

import pytest
from fastmcp.exceptions import ToolError

from tests.helpers import register_module_tools
from tests.offline import OfflineClient
from tools.etf import daily_nav, holdings, info, monthly_stats
from utils.sitca import available_months, fund_name_key, holdings_by_class, parse_holdings, query_rows

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

    def cells(r, tag):
        return "".join(f"<{tag}>{c}</{tag}>" for c in r)

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
    with pytest.raises(ToolError, match="sort_by 必須是"):
        fn(sort_by="volume")
    with pytest.raises(ToolError, match="limit 必須介於"):
        fn(limit=0)
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
    with pytest.raises(ToolError, match="period 必須是 YYYYMM 且介於 202605～202608"):
        fn(code="0050", period="202001")
    with pytest.raises(ToolError, match="months 必須介於 1～24"):
        fn(code="0050", months=25)
    assert "查無 ETF 代號 9999" in fn(code="9999")


def test_monthly_stats_ranking_and_column_guard():
    fn = register_module_tools(monthly_stats, OfflineClient(_stats_routes([])))["get_etf_monthly_stats"]
    lines = fn(sort_by="net_flow").splitlines()
    assert lines[0] == "【ETF 淨申購金額排行】2026-08（共 2 檔，列出前 2 檔）"
    assert lines[2].startswith("1. 00878 簡稱00878 | 規模 1,000.0 億")
    assert fn(sort_by="scale").splitlines()[2].startswith("1. 0050")
    with pytest.raises(ToolError, match="sort_by 必須是"):
        fn(sort_by="nav")
    with pytest.raises(ValueError, match="欄位已變更"):
        monthly_stats.records([["序號", "證券代號"], ["1", "0050"]])


# ---------- get_etf_holdings ----------

HOLD_HEADER = ["基金名稱", "名次", "標的種類", "標的代號 或<br>Bloomberg<br>Isin Code", "標的名稱", "金額", "擔保機構**",
               "次順位債券**", "受益權單位數***", "占基金淨資產價值<br>之比例(%)"]


def _holdings_html(funds, header=HOLD_HEADER):
    """IN2629 的結果表：沒有 id、表頭用 <td>…</th>、基金名稱以 rowspan 跨列，外面還包著排版表格。"""
    head = "".join(f"<td class=DTHeader nowrap align=center>{h}</th>" for h in header)
    body = ""
    for name, rows in funds:
        for i, r in enumerate(rows):
            first = f"<td class='DTeven' rowspan='{len(rows)}'>{name}</td>" if i == 0 else ""
            body += "<tr>" + first + "".join(f"<td class='DTeven'>{c}</td>" for c in r) + "</tr>"
    return f"<table id='outer'><tr><td><table><tr>{head}</tr>{body}</table></td></tr></table>".encode("utf-8")


def _hold_row(rank, code, name, amount, pct, kind="國內上市"):
    return [rank, kind, code, name, amount, "", "", "0", pct]


def test_parse_holdings_handles_rowspan_and_malformed_header():
    header, funds = parse_holdings(_holdings_html([
        ("甲ETF基金 (本基金之配息來源可能為收益平準金)", [_hold_row("1", "2330", "台積電", "100", "50.00"), _hold_row("2", "2454", "聯發科", "10", "5.00")]),
        ("乙ETF基金", [_hold_row("1", "2317", "鴻海", "1", "9.00")]),
    ]).decode("utf-8"))
    assert header[3] == "標的代號 或 Bloomberg Isin Code" and header[-1] == "占基金淨資產價值 之比例(%)"
    assert list(funds) == ["甲ETF基金 (本基金之配息來源可能為收益平準金)", "乙ETF基金"]
    assert funds["甲ETF基金 (本基金之配息來源可能為收益平準金)"][1][3] == "聯發科"
    assert parse_holdings("<html>改版</html>") == ([], {})


def test_fund_name_key_drops_disclaimer_and_share_class_only():
    assert fund_name_key("中國信託日經高股息50 ETF基金 (本子基金之配息來源可能為收益平準金)") == "中國信託日經高股息50ETF基金"
    assert fund_name_key("國泰…20年期(以上)美國公債指數基金-新台幣(配息)") == "國泰…20年期(以上)美國公債指數基金"
    assert fund_name_key("國泰…20年期(以上)美國公債指數基金-美元") == "國泰…20年期(以上)美國公債指數基金"
    assert fund_name_key("中國信託新興亞洲(不含中國)美元精選綜合債券ETF基金") == "中國信託新興亞洲(不含中國)美元精選綜合債券ETF基金"
    assert fund_name_key("元大台灣50單日正向2倍基金") != fund_name_key("元大台灣50單日反向1倍基金")


class _FakeHoldingsPage:
    """IN2629/IN2630: GET → 期間 postback（換新 VIEWSTATE）→ 依類別查詢，查詢必須帶 postback 回來的 VIEWSTATE."""

    def __init__(self, periods, funds_by_period):
        self.periods, self.funds_by_period, self.queries = periods, funds_by_period, []

    def _page(self, viewstate):
        options = "".join(f'<option value="{p}">{p}</option>' for p in self.periods)
        return (f'<input type="hidden" name="__VIEWSTATE" id="__VIEWSTATE" value="{viewstate}" />'
                f'<select name="ctl00$ContentPlaceHolder1$ddlQ_YM" id="x">{options}</select>').encode("utf-8")

    def __call__(self, params, body):
        prefix = "ctl00$ContentPlaceHolder1$"
        if not body:
            return self._page("vs-get")
        if body.get("__EVENTTARGET") == prefix + "ddlQ_YM":
            assert body["__VIEWSTATE"] == "vs-get" and body[prefix + "rdo1"] == "rbClass"
            return self._page(f"vs-{body[prefix + 'ddlQ_YM']}")
        ym, cls = body[prefix + "ddlQ_YM"], body[prefix + "ddlQ_Class"]
        assert body["__VIEWSTATE"] == f"vs-{ym}", "查詢必須沿用期間 postback 回傳的 VIEWSTATE"
        assert prefix + "ddlQ_Comid" not in body, "停用中的欄位不應送出"
        self.queries.append((ym, cls))
        return _holdings_html(self.funds_by_period.get((ym, cls), []))


def _holdings_routes(monthly, quarterly=None):
    def statement(params, body):
        if params["txtemcode"] == "0050,":
            row = _stat_row("0050", "111", "不分級別", "1", "1")
            return _grid(STATEMENT_HEADER, [row])
        if params["txtfund"] == "111," and params["txtYM"] == "202607":
            row = _stat_row("-", "111", "不分級別", "1", "1")
            row[1], row[5] = "AH11", "舊名台灣50基金"  # 該月的名稱與現在不同
            return _grid(STATEMENT_HEADER, [row])
        return _grid(STATEMENT_HEADER, [])

    routes = {"etf_statement.aspx": _month_page(["202608", "202607"]), "etf_statement2.aspx": statement,
              "IN2629.aspx": monthly}
    if quarterly:
        routes["IN2630.aspx"] = quarterly
    return routes


def test_holdings_by_class_posts_period_then_query():
    page = _FakeHoldingsPage(["202607", "202608"], {("202607", "AH11"): [("X基金", [_hold_row("1", "2330", "台積電", "1", "1")])]})
    header, funds = holdings_by_class(OfflineClient({"IN2629.aspx": page}), "IN2629.aspx", "202607", "AH11")
    assert list(funds) == ["X基金"] and page.queries == [("202607", "AH11")]


def test_etf_holdings_latest_and_past_period_names():
    monthly = _FakeHoldingsPage(["202607", "202608"], {
        ("202608", "AH11"): [
            ("別檔基金", [_hold_row("1", "2317", "鴻海", "1", "1")]),
            ("基金111 (本基金之配息來源可能為收益平準金)", [
                _hold_row("1", "2330", "台積電", "1,367,244,000,000", "57.35"),
                _hold_row("2", "US912810UK24", "US TREASURY", "52,000,000", "0.40", kind="政府公債"),
            ]),
        ],
        ("202607", "AH11"): [("舊名台灣50基金", [_hold_row("1", "2330", "台積電", "100,000,000", "50.00")])],
    })
    fn = register_module_tools(holdings, OfflineClient(_holdings_routes(monthly)))["get_etf_holdings"]
    text = fn("0050")
    assert text.splitlines()[0] == "【0050 簡稱0050 持股明細】基金111"
    assert "資料期間 2026-08｜每月前十大持股｜共 2 檔，合計占淨值 57.75%" in text
    assert "1. 台積電（2330） | 國內上市 | 占淨值 57.35% | 金額 13,672.44 億元" in text
    assert "2. US TREASURY（US912810UK24） | 政府公債 | 占淨值 0.40% | 金額 5,200 萬元" in text
    assert "鴻海" not in text
    past = fn("0050", period="202607")  # 過去期間改用該月 ETF 專區的名稱
    assert "【0050 簡稱0050 持股明細】舊名台灣50基金" in past and "資料期間 2026-07" in past


def test_etf_holdings_quarterly_ranks_by_weight_and_messages():
    quarterly_header = [h for h in HOLD_HEADER if h != "名次"]

    def q_row(code, name, pct):
        return ["國內上市", code, name, "1", "", "", "0", pct]


    class Quarterly(_FakeHoldingsPage):
        def __call__(self, params, body):
            if body and "BtnQuery" in str(body):
                super().__call__(params, body)
                return _holdings_html([("基金111", [q_row("2454", "聯發科", "5.00"), q_row("2330", "台積電", "57.00")])],
                                      header=quarterly_header)
            return super().__call__(params, body)

    monthly = _FakeHoldingsPage(["202608"], {})
    fn = register_module_tools(holdings, OfflineClient(_holdings_routes(monthly, Quarterly(["202606"], {}))))["get_etf_holdings"]
    lines = fn("0050", quarterly=True).splitlines()
    assert "每季占淨值 1% 以上持股｜共 2 檔" in lines[1]
    assert lines[3].startswith("1. 台積電") and lines[4].startswith("2. 聯發科")

    assert "基金投資明細中沒有 0050" in fn("0050")  # 該月明細裡沒有這檔（如反向型）
    with pytest.raises(ToolError, match="period 必須是季末月 YYYYMM，可查 202606～202606"):
        fn("0050", period="202605", quarterly=True)
    assert "查無 ETF 代號 9999" in fn("9999")
    with pytest.raises(ToolError, match="請提供 ETF 代號"):
        fn(" ")


def test_etf_holdings_column_guard():
    page = _FakeHoldingsPage(["202608"], {})

    def renamed_columns(params, body):
        if body and "BtnQuery" in str(body):
            return _holdings_html([("基金111", [["1", "2330"]])], header=["基金名稱", "名次", "代號"])
        return page(params, body)

    fn = register_module_tools(holdings, OfflineClient(_holdings_routes(renamed_columns)))["get_etf_holdings"]
    with pytest.raises(ToolError, match="欄位已變更"):
        fn("0050")
