"""sources/mops/insiders.py 與 get_company_board_shareholdings／get_company_insider_holding_changes 的單元測試（不打網路）。

titles（含「本月增加」「本月減少」兩組、結尾帶換行的欄名）與資料列取自公開資訊觀測站真實回應（2330，民國 115 年 9 月）；
上游真實格式由 tests/contract/test_mops_api.py::TestInsiderHoldingsGateway 驗證。
"""

import pytest
from fastmcp.exceptions import ToolError

from sources.mops.insiders import board_holdings, insider_changes, period_body
from tests.helpers import register_module_tools
from tests.offline import OfflineClient
from tools.mops import insiders
from utils.errors import UpstreamFormatError

pytestmark = pytest.mark.offline


def _titles(*items):
    return [{"main": i} if isinstance(i, str) else {"main": i[0], "sub": [{"main": s} for s in i[1]]} for i in items]


Q6_TITLES = _titles(
    "身份別", "姓名", "持股種類", "選任當時持有股數", "上月實際持有股數", "截至上月底保留運用決定權信託股數", "截至上月底累計設質",
    "截至上月底累計持有私募股票股數",
    ("本月增加", ["自有股數(集中)", "自有股數(其它原因－不含私募)", "私募股數", "保留運用決定權信託股數", "設定質權股數"]),
    ("本月減少", ["自有股數(集中)", "自有股數(其它原因－不含私募)", "私募股數", "保留運用決定權信託股數", "解除質權股數\n"]),
    "本月實際自有持有股數", "截至本月底分戶集保股數", "截至本月底保留運用決定權信託股數", "截至本月底累計設質",
    "截至本月底累計持有私募股票股數", "身份別備註")
CHAIRMAN = ["董事長本人", "魏哲家", "普通股", "6,392,834", "7,452,349", "0", "1,600,000", "0", "0", "204,375", "0", "0", "0",
            "0", "0", "0", "0", "0", "7,656,724", "0", "0", "1,600,000", "0", "兼總經理"]
SPOUSE = ["董事長本人之配偶及未成年子女", "", "普通股", "0", "700,261", "0", "0", "0", "0", "0", "0", "0", "0", "0", "0", "0",
          "0", "0", "700,261", "0", "0", "0", "0", ""]
STAPAP1_TITLES = _titles("職稱", "姓名", "選任時持股", "目前持股", "設質股數", "設質股數佔持股比例",
                         ("配偶、未成年子女及利用他人名義持有部份", ["內部人關係人目前持股合計", "設質股數", "設質比例"]))
BOARD = [["董事長本人", "魏哲家", "6,392,834", "7,656,724", "1,600,000", "20.89%", "700,261", "0", "0.00%"],
         ["董事本人", "行政院國家發展基金管理會", "1,653,709,980", "1,653,709,980", "0", "0.00%", "0", "0", "0.00%"]]
TOTAL = {"nonIndependentDirector": ["1,685,839,379", "1,600,000", "0.09%"], "independentDirectorSupervisor": ["126,826", "0", "0.00%"]}


def ok(result):
    return {"code": 200, "message": "查詢成功", "result": result}


def q6_reply(rows=None, titles=None):
    return ok({"companyAbbreviation": "台積電", "year": "115", "month": "09", "note": "", "reason": "",
               "titles": titles or Q6_TITLES, "data": [CHAIRMAN, SPOUSE] if rows is None else rows})


def stapap1_reply(rows=None):
    return ok({"parentCompany": {"companyAbbreviation": "台積電", "yymm": "11509", "titles": STAPAP1_TITLES,
                                 "data": BOARD if rows is None else rows, "total": TOTAL,
                                 "note": "備註：該公司未設置 協理及相當等級者\n", "reason": "未設置經理人之理由： 無\n"},
               "subsidiary": {}})


NOT_FOUND = {"code": 406, "message": "查無相符資料", "result": None}


def test_request_body():
    assert period_body("2330") == {"companyId": "2330", "dataType": "1", "year": "", "month": "", "subsidiaryCompanyId": ""}
    assert period_body("2330", 115, 6) == {"companyId": "2330", "dataType": "2", "year": "115", "month": "06",
                                           "subsidiaryCompanyId": ""}


def test_insider_changes_find_the_two_groups_by_title():
    report = insider_changes(OfflineClient({"/mops/api/query6_1": q6_reply()}), "2330")
    chairman, spouse = report.changes
    assert (report.name, report.year, report.month) == ("台積電", "115", "09")
    assert (chairman.identity, chairman.name, chairman.last_month, chairman.this_month, chairman.pledged) == (
        "董事長本人", "魏哲家", 7452349, 7656724, 1600000)
    assert [t for t, _ in chairman.moves][:2] == ["本月增加 自有股數(集中)", "本月增加 自有股數(其它原因－不含私募)"]
    assert chairman.moves[-1] == ("本月減少 解除質權股數", 0)  # the title's trailing line break is gone
    assert chairman.changed and not spouse.changed and spouse.name == ""


def test_board_holdings_keep_the_published_columns():
    report = board_holdings(OfflineClient({"/mops/api/stapap1": stapap1_reply()}), "2330", 115, 9)
    assert report.columns[:2] == ("選任時持股", "目前持股")
    assert report.columns[-1] == "配偶、未成年子女及利用他人名義持有部份 設質比例"
    first = report.holdings[0]
    assert (first.title, first.name, first.values[:4]) == ("董事長本人", "魏哲家", ("6,392,834", "7,656,724", "1,600,000", "20.89%"))
    assert report.totals["nonIndependentDirector"] == ("1,685,839,379", "1,600,000", "0.09%")
    assert (report.note, report.reason) == ("備註：該公司未設置 協理及相當等級者", "未設置經理人之理由： 無")


def test_no_data_and_changed_titles():
    assert insider_changes(OfflineClient({"/mops/api/query6_1": NOT_FOUND}), "9999") is None
    assert board_holdings(OfflineClient({"/mops/api/stapap1": stapap1_reply([])}), "2330") is None
    renamed = _titles("身份別", "姓名", "持股種類", "選任當時持有股數", "上月持股") + Q6_TITLES[5:]
    with pytest.raises(UpstreamFormatError, match="上月實際持有股數"):
        insider_changes(OfflineClient({"/mops/api/query6_1": q6_reply(titles=renamed)}), "2330")
    with pytest.raises(UpstreamFormatError, match="對不上"):
        insider_changes(OfflineClient({"/mops/api/query6_1": q6_reply([CHAIRMAN[:23]])}), "2330")


def _tool(path, payload, name):
    return register_module_tools(insiders, OfflineClient({path: payload}))[name]


def test_changes_tool_prints_the_same_lines_as_before_the_gateway():
    fn = _tool("/mops/api/query6_1", q6_reply(), "get_company_insider_holding_changes")
    text = fn("2330")
    assert text.startswith("【台積電(2330) 內部人持股異動 民國115年09月】（共 2 位申報人，本月有異動 1 位）\n")
    assert ("董事長本人 魏哲家（普通股）| 上月持股:7,452,349 → 本月持股:7,656,724 | 累計設質:1,600,000 | "
            "本月增加 自有股數(其它原因－不含私募):204,375") in text
    assert "配偶" not in text
    assert "董事長本人之配偶及未成年子女（普通股）| 上月持股:700,261 → 本月持股:700,261 | 累計設質:0" in fn(
        "2330", only_changed=False)


def test_board_tool_prints_the_same_lines_as_before_the_gateway():
    text = _tool("/mops/api/stapap1", stapap1_reply(), "get_company_board_shareholdings")("2330", "2026", "9")
    assert text.startswith("【台積電(2330) 董監事持股餘額明細 民國115年09月】\n欄位: 選任時持股 | 目前持股 | 設質股數 | "
                           "設質股數佔持股比例 | 配偶、未成年子女及利用他人名義持有部份 內部人關係人目前持股合計 | ")
    assert "董事長本人 魏哲家: 6,392,834 | 7,656,724 | 1,600,000 | 20.89% | 700,261 | 0 | 0.00%" in text
    assert "  非獨立董事: 1,685,839,379 | 1,600,000 | 0.09%" in text
    assert text.endswith("備註：該公司未設置 協理及相當等級者\n未設置經理人之理由： 無")


def test_period_arguments():
    fn = _tool("/mops/api/stapap1", stapap1_reply(), "get_company_board_shareholdings")
    with pytest.raises(ToolError, match="同時指定"):
        fn("2330", year="2026")
    with pytest.raises(ToolError, match="1～12"):
        fn("2330", year="2026", month="13")
