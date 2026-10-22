"""sources/tpex/etf.py 的單元測試（不打網路）。get_etf_info 的合併與輸出見 test_etf_unit.py。

回應取自櫃買中心真實回應（2026-10-22 ETF/list domestic、006201 的 ETF/detail）；上游真實格式由
tests/contract/test_etf_api.py::TestTpexEtfPages 驗證。
"""

import pytest

from sources.tpex.etf import tpex_etf_detail, tpex_etfs
from tests.offline import OfflineClient
from utils.errors import UpstreamFormatError

pytestmark = pytest.mark.offline

LIST = {"stat": "ok", "date": "20261022", "tables": [{
    "title": "國內成分股ETF", "title2": "", "totalCount": 3, "fields": ["證券代號", "ETF簡稱", "上櫃日期"],
    "data": [["006201", "元大富櫃50", "100/01/27"], ["00928", "中信上櫃ESG30", "112/05/24"]], "notes": [], "summary": []}]}
SPEC_FIELDS = ["名稱", "ETF簡稱", "證券代號", "ETF類別", "上櫃日期", "基金經理公司", "標的指數", "管理費", "保管費", "基金經理公司網站"]
SPEC_ROW = ["元大櫃買ETF傘型證券投資信託基金之富櫃50證券投資信託基金", "元大富櫃50", "006201", "被動式國內成分股ETF",
            "2011/01/27", "元大證券投資信託股份有限公司", "櫃買富櫃五十指數",
            "100億(含)以下: 0.40% ; 100~300億(含): 0.34%; 300億以上: 0.30%", "0.035%",
            '<a href="http://www.yuantaetfs.com/" target="_blank">http://www.yuantaetfs.com/</a>']
PCF = {"title": "申購買回清單PCF", "fields": [""],
       "data": [['<a href="https://www.yuantaetfs.com/tradeInfo/pcf/006201" target="_blank">申購買回清單PCF</a>']]}
INDEX = {"title": "標的指數資訊", "fields": ["標的指數名稱", "指數編製機構"],
         "data": [["櫃買富櫃五十指數", "財團法人中華民國證券櫃檯買賣中心"]]}


def detail(*tables):
    return {"stat": "ok", "html": [], "tables": list(tables)}


def test_list_by_field_name():
    seen = []

    def route(_params, form):
        seen.append(dict(form))
        return LIST

    etfs = tpex_etfs(OfflineClient({"ETF/list": route}), "domestic")
    assert [(e.code, e.name, e.listed) for e in etfs] == [("006201", "元大富櫃50", "100/01/27"),
                                                          ("00928", "中信上櫃ESG30", "112/05/24")]
    assert seen == [{"type": "domestic", "response": "json"}]


def test_detail_sections_strip_links_and_leave_out_pcf():
    spec = {"title": "商品規格", "fields": SPEC_FIELDS, "data": [SPEC_ROW]}
    sections = tpex_etf_detail(OfflineClient({"ETF/detail": detail(spec, PCF, INDEX)}), "domestic", "006201")
    assert [s.title for s in sections] == ["商品規格", "標的指數資訊"]
    items = dict(sections[0].items)
    assert items["管理費"].startswith("100億(含)以下: 0.40%") and items["基金經理公司網站"] == "http://www.yuantaetfs.com/"


def test_format_changes_raise():
    renamed = {**LIST, "tables": [{**LIST["tables"][0], "fields": ["代號", "ETF簡稱", "上櫃日期"]}]}
    with pytest.raises(UpstreamFormatError, match="證券代號"):
        tpex_etfs(OfflineClient({"ETF/list": renamed}), "domestic")
    with pytest.raises(UpstreamFormatError, match="結構已變更"):
        tpex_etfs(OfflineClient({"ETF/list": {"stat": "ok", "data": []}}), "domestic")
    with pytest.raises(UpstreamFormatError, match="不是 JSON"):
        tpex_etfs(OfflineClient({"ETF/list": b"<html>busy</html>"}), "domestic")
    short = {"title": "商品規格", "fields": SPEC_FIELDS, "data": [SPEC_ROW[:-1]]}
    with pytest.raises(UpstreamFormatError, match="一列對應"):
        tpex_etf_detail(OfflineClient({"ETF/detail": detail(short)}), "domestic", "006201")
