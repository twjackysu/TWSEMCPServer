"""sources/mops/major_news.py 與 get_company_major_news 的單元測試（不打網路）。

titles 與資料列的形狀取自公開資訊觀測站真實回應（t05st01 2330、t05st02 115/10/21、t05st01_detail 115/10/15）；
上游真實格式由 tests/contract/test_mops_api.py::TestMajorNewsGateway 驗證。
"""

from datetime import datetime

import pytest

from sources.mops.major_news import NewsLink, company_news, market_news, news_detail
from tests.helpers import register_module_tools
from tests.offline import OfflineClient
from tools.mops import major_news
from utils.errors import UpstreamFormatError

pytestmark = pytest.mark.offline

COMPANY_TITLES = [{"main": t} for t in ("公司代號", "公司名稱", "發言日期", "發言時間", "主旨", "詳細資料")]
MARKET_TITLES = [{"main": t} for t in ("發言日期", "發言時間", "公司代號", "公司名稱", "主旨", "詳細資料")]
DETAIL_TITLES = [{"main": t} for t in ("序號", "發言日期", "發言時間", "發言人", "發言人職稱", "發言人電話", "主旨",
                                       "符合條款", "事實發生日", "說明")]


def ok(result):
    return {"code": 200, "message": "查詢成功", "result": result}


NOT_FOUND = {"code": 406, "message": "查無相符資料", "result": None}


def link(api, code, serial=1, kind="sii", day="1151015"):
    return {"apiName": api, "parameters": {"companyId": code, "marketKind": kind, "enterDate": day,
                                           "serialNumber": str(serial)}}


def detail_reply(text="1.事實發生日:115/10/15\n2.公司名稱:台灣積體電路製造股份有限公司\n"):
    return ok({"companyAbbreviation": "台積電", "titles": DETAIL_TITLES, "data": [[
        "1", "115/10/15", "15:21:38", "黃仁昭                                     ", "資深副總經理暨財務長",
        "03-563-6688         ", "台積公司2026年第三季每股盈餘新台幣29.43元               ", "第51款", "115/10/15", text]]})


def test_company_rows_and_links():
    rows = [["2330", "台積電", "115/10/15", "15:21:38", "台積公司2026年第三季每股盈餘新台幣29.43元", link("t05st01_detail", "2330")],
            ["2330", "台積電", "115/01/02", "16:56:08", "本公司代子公司 TSMC Global Ltd. 公告取得固定收益證券", "?"]]
    news = company_news(OfflineClient({"/mops/api/t05st01": ok({"companyAbbreviation": "台積電", "titles": COMPANY_TITLES,
                                                                "data": rows})}), "2330", 115)
    eps, other = news.announcements
    assert (news.name, eps.code, eps.date, eps.time, eps.market) == ("台積電", "2330", "115/10/15", "15:21:38", "sii")
    assert eps.link == NewsLink("t05st01_detail", {"companyId": "2330", "marketKind": "sii", "enterDate": "1151015",
                                                   "serialNumber": "1"})
    assert (other.link, other.market) == (None, "")


def test_market_rows_keep_line_breaks_and_the_request():
    seen = []

    def route(_params, body):
        seen.append(dict(body))
        return ok({"titles": MARKET_TITLES, "data": [
            ["115/10/21", "17:32:37", "3712", "永崴投控", "公告本公司115年第一次\r\n股東臨時會重要決議事項",
             link("t05st02_detail", "3712", kind="otc", day="1151021")]]})

    (a,) = market_news(OfflineClient({"/mops/api/t05st02": route}), "20261021")
    assert seen == [{"year": "115", "month": "10", "day": "21"}]
    assert (a.code, a.name, a.market, a.subject) == ("3712", "永崴投控", "otc", "公告本公司115年第一次\r\n股東臨時會重要決議事項")
    assert market_news(OfflineClient({"/mops/api/t05st02": NOT_FOUND}), "20261025") == []


def test_detail_is_stripped():
    d = news_detail(OfflineClient({"/mops/api/t05st01_detail": detail_reply()}), NewsLink("t05st01_detail", {}))
    assert (d.spokesperson, d.spokesperson_title, d.clause, d.fact_date) == ("黃仁昭", "資深副總經理暨財務長", "第51款", "115/10/15")
    assert d.subject == "台積公司2026年第三季每股盈餘新台幣29.43元" and d.text.endswith("有限公司")


def test_changed_titles_or_rows_are_an_error():
    renamed = [{"main": "代號"}] + COMPANY_TITLES[1:]
    with pytest.raises(UpstreamFormatError, match="公司代號"):
        company_news(OfflineClient({"/mops/api/t05st01": ok({"titles": renamed, "data": [["2330"] * 6]})}), "2330", 115)
    with pytest.raises(UpstreamFormatError, match="對不上"):
        market_news(OfflineClient({"/mops/api/t05st02": ok({"titles": MARKET_TITLES, "data": [["115/10/21"] * 5]})}),
                    "20261021")


def test_company_tool_newest_first_with_full_text_capped():
    rows = [["6488", "環球晶", f"115/09/{d:02d}", "10:00:00", f"主旨{d}", link("t05st01_detail", "6488", d, "otc")]
            for d in range(1, 16)]
    client = OfflineClient({"/mops/api/t05st01": ok({"companyAbbreviation": "環球晶", "titles": COMPANY_TITLES, "data": rows}),
                            "/mops/api/t05st01_detail": detail_reply("說明\n內容")})
    text = register_module_tools(major_news, client)["get_company_major_news"]("6488", year="2026")
    assert text.startswith("【環球晶(6488) 重大訊息 民國115年】（共 15 則，由新到舊，顯示第 1–10 則，每頁最多 10 則含全文）\n")
    assert ("115/09/15 10:00:00 | 主旨15\n"
            "  符合條款:第51款 | 事實發生日:115/10/15 | 發言人:黃仁昭（資深副總經理暨財務長）\n"
            "  說明:說明\n內容") in text
    assert "115/09/05" not in text and text.count("說明:說明") == 10 and "offset=10" in text


def test_market_tool_walks_back_and_filters_market(monkeypatch):
    monkeypatch.setattr(major_news, "taipei_today", lambda: datetime(2026, 9, 30))
    asked = []

    def route(_params, body):
        asked.append(body["day"])
        if body["day"] != "28":
            return NOT_FOUND
        return ok({"titles": MARKET_TITLES, "data": [
            ["115/09/28", "20:00:00", "6488", "環球晶", "主旨\n換行", link("t05st02_detail", "6488", kind="otc")],
            ["115/09/28", "20:01:00", "2330", "台積電", "主旨", link("t05st02_detail", "2330")]]})

    fn = register_module_tools(major_news, OfflineClient({"/mops/api/t05st02": route}))["get_company_major_news"]
    text = fn(market="otc")
    assert asked == ["30", "29", "28"] and "查詢日 20260928" in text
    assert "115/09/28 20:00:00 | 上櫃 6488 環球晶 | 主旨 換行" in text and "2330" not in text
