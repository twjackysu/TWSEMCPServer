"""sources/mops/investor_conference.py 的單元測試（不打網路）。工具的月份補零、排序與參數檢查見 test_mops_unit.py。

表頭標記與資料列取自公開資訊觀測站真實回應（民國 115 年 1 月、99 年 1 月上市，114 年 7 月興櫃）；上游真實格式由
tests/contract/test_mops_api.py::TestInvestorConferenceGateway 驗證。
"""

import pytest

from sources.mops.investor_conference import investor_conferences
from tests.offline import OfflineClient
from utils.errors import UpstreamFormatError

pytestmark = pytest.mark.offline

TOP = ["公司代號", "公司名稱", "召開法人說明會日期", "召開法人說明會時間", "召開法人說明會地點", "法人說明會擇要訊息",
       "法人說明會簡報內容", "公司網站是否提供法人說明會相關資訊", "影音連結資訊", "其他應敘明事項", "歷年法人說明會"]
SUB = ["中文檔案", "英文檔案"]
MAKALOT = ["1477", "聚陽", "115/01/08", "14:00", "線上法說會", "介紹本公司之營運概況及經營策略等財務業務相關資料",
           "147720251110M002.pdf", "147720251110E002.pdf", "http://www.makalot.com.tw", "", "無", ""]
# 興櫃／公開發行：網站欄名不同，沒有影音連結資訊
ROTC_TOP = TOP[:7] + ["公司網站是否提供法人說明會內容", "其他應敘明事項", "歷年法人說明會"]
STEMINENT = ["7729", "仲恩生醫", "114/07/17", "14:30", "台北市內湖區文湖街12號4樓之1 (本公司101會議室)",
             "說明本公司營運成果以及未來展望。", "772920250716M001.pdf", "772920250716E001.pdf",
             "https://steminent.com/article/lists?article_category_id=2&article_id=11&page=1",
             "完整財務業務資訊請至公開資訊觀測站之法人說明會一覽表或法說會項目下查閱。", ""]
ACC = ["1102", "亞泥", "99/01/11", "09:00", "北京", "", "110220100108M001.pdf", "", "www.acc.com.tw", "",
       "本公司應德意志證券之邀將於99年1月11及12日參加於北京舉辦之投資說明會", ""]


def header(top=TOP, sub=SUB) -> str:
    spans = "".join(f"<th class='tblHead' nowrap {'colspan' if t == '法人說明會簡報內容' else 'rowspan'}='2'><b>{t}</b></th>"
                    for t in top)
    return f"<thead><tr class='tblHead'>{spans}</tr><tr>" + "".join(f"<th><b>{s}</b></th>" for s in sub) + "</tr></thead>"


def page(*rows, top=TOP, sub=SUB) -> bytes:
    body = "".join("<tr class='even'>" + "".join(f"<td>{c or '&nbsp;'}</td>" for c in r) + "</tr>" for r in rows)
    return f"<table id='myTable' class='hasBorder'>{header(top, sub)}{body}</table>".encode("utf-8")


def _client(body):
    return OfflineClient({"/mops/web/ajax_t100sb02_1": body})


def test_rows_become_conferences_with_both_file_columns():
    makalot, acc = investor_conferences(_client(page(MAKALOT, ACC)), "sii", 115, 1)
    assert (makalot.code, makalot.name, makalot.date, makalot.time, makalot.place) == (
        "1477", "聚陽", "115/01/08", "14:00", "線上法說會")
    assert (makalot.file_zh, makalot.file_en, makalot.website, makalot.other) == (
        "147720251110M002.pdf", "147720251110E002.pdf", "http://www.makalot.com.tw", "無")
    assert (acc.summary, acc.file_en) == ("", "")


def test_rotc_and_pub_pages_name_the_website_column_differently():
    (c,) = investor_conferences(_client(page(STEMINENT, top=ROTC_TOP)), "rotc", 114, 7)
    assert (c.code, c.file_zh, c.video) == ("7729", "772920250716M001.pdf", "")
    assert c.website.startswith("https://steminent.com/") and c.other.startswith("完整財務業務資訊")


def test_request_form():
    forms = []

    def route(_params, form):
        forms.append(dict(form))
        return page(MAKALOT)

    investor_conferences(_client(route), "otc", 115, 9, "1477")
    investor_conferences(_client(route), "sii", 115)
    assert {k: forms[0][k] for k in ("TYPEK", "year", "month", "co_id")} == {
        "TYPEK": "otc", "year": "115", "month": "09", "co_id": "1477"}
    assert forms[1]["month"] == "" and forms[1]["co_id"] == ""


def test_no_data_unexpected_page_and_changed_header():
    assert investor_conferences(_client("<html><center>查無資料</center></html>".encode("utf-8")), "sii", 115, 1) == []
    with pytest.raises(UpstreamFormatError, match="非預期頁面"):
        investor_conferences(_client(b"<html>FOR SECURITY REASONS</html>"), "sii", 115, 1)
    with pytest.raises(UpstreamFormatError, match="第二列表頭"):
        investor_conferences(_client(page(MAKALOT, sub=["中文", "英文"])), "sii", 115, 1)
    with pytest.raises(UpstreamFormatError, match="公司網站是否提供法人說明會相關資訊"):
        investor_conferences(_client(page(MAKALOT, top=TOP[:7] + ["網站"] + TOP[8:])), "sii", 115, 1)
    renamed = TOP[:2] + ["日期"] + TOP[3:]
    with pytest.raises(UpstreamFormatError, match="召開法人說明會日期"):
        investor_conferences(_client(page(MAKALOT, top=renamed)), "sii", 115, 1)
    with pytest.raises(UpstreamFormatError, match="11 格"):
        investor_conferences(_client(page(MAKALOT[:11])), "sii", 115, 1)
