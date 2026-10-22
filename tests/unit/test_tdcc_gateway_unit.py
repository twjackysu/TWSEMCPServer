"""sources/tdcc 的單元測試（不打網路）。工具的趨勢、週快取與查無訊息見 test_free_sources_unit.py。

CSV 列與結果表取自集保真實回應（2330，開放資料 2026-10-08、查詢頁 2026-10-08 那週）；上游真實格式由
tests/contract/test_tdcc_macro_api.py 驗證。
"""

from datetime import date
from decimal import Decimal

import pytest

from sources.tdcc.levels import TOTAL
from sources.tdcc.opendata import latest_distribution
from sources.tdcc.qry_stock import StockQuery
from tests.offline import OfflineClient
from utils.errors import UpstreamFormatError

pytestmark = pytest.mark.offline

CSV_HEADER = "資料日期,證券代號,持股分級,人數,股數,占集保庫存數比例%"
CSV_2330 = ["20261008,2330  ,1,2459344,287438824,1.10", "20261008,2330  ,15,1482,21987181886,84.78",
            "20261008,2330  ,16,1,6000,0.00", "20261008,2330  ,17,3007088,25932370067,100.00"]


def csv_body(*lines, header=CSV_HEADER):
    return ("﻿" + "\n".join((header,) + lines) + "\n").encode("utf-8")


def _csv_client(body):
    return OfflineClient({"getOD.ashx?id=1-5": body})


def test_csv_rows_of_one_code():
    body = csv_body(*CSV_2330, "20261008,0050  ,17,3565195,22233000000,100.00")
    dist = latest_distribution(_csv_client(body), "2330")
    assert dist.date == date(2026, 10, 8)
    assert [(h.level, h.people, h.shares, h.pct) for h in dist.levels] == [
        (1, 2459344, 287438824, Decimal("1.10")), (15, 1482, 21987181886, Decimal("84.78")),
        (16, 1, 6000, Decimal("0.00")), (17, 3007088, 25932370067, Decimal("100.00"))]
    assert latest_distribution(_csv_client(body), "9999") is None


def test_csv_format_changes_raise():
    with pytest.raises(UpstreamFormatError, match="占集保庫存數比例%"):
        latest_distribution(_csv_client(csv_body(*CSV_2330, header=CSV_HEADER.replace("%", ""))), "2330")
    with pytest.raises(UpstreamFormatError, match="資料列有 5 欄"):
        latest_distribution(_csv_client(csv_body("20261008,2330  ,1,2459344,287438824")), "2330")
    with pytest.raises(UpstreamFormatError, match="數字格式"):
        latest_distribution(_csv_client(csv_body("20261008,2330  ,1,N/A,287438824,1.10")), "2330")


def query_page(token, dates=("20261016", "20261008")):
    options = "".join(f'\n    <option value="{d}" >{d}</option>' for d in dates)
    return (f'<input type="hidden" name="SYNCHRONIZER_TOKEN" value="{token}" id="SYNCHRONIZER_TOKEN" />'
            f'<input type="hidden" name="firDate" value="{dates[0]}" id="firDate" />'
            f'<select name="scaDate" id="scaDate">{options}\n</select>').encode("utf-8")


HEAD = ("<table class=\"table\"><thead><tr><th>序</th><th>持股/單位數分級</th><th>人數</th><th>股數/單位數</th>"
        "<th>占集保庫存數比例 (%)</th></tr></thead>")
ROWS_20261008 = [("1", "1-999", "2,459,344", "287,438,824", "1.10"),
                 ("15", "1,000,001以上", "1,482", "21,987,181,886", "84.78"),
                 ("16", "差異數調整（說明4）", "", "-6,000", "-0.00"),
                 ("17", "合　計", "3,007,088", "25,932,370,067", "100.00")]
NO_DATA = '<tr><td align="center" colspan="5"><span class="font" style="color: #ff0000;">查無此資料</span></td></tr>'


def result_page(token, rows=ROWS_20261008, head=HEAD):
    body = "".join("<tr>" + "".join(f'<td align="right">{c}</td>' for c in r) + "</tr>" for r in rows)
    tok = f'<input type="hidden" name="SYNCHRONIZER_TOKEN" value="{token}" />' if token else ""
    return f"<html>{tok}{head}{body}</table></html>".encode("utf-8")


class Site:
    """Answers GET with the query page and each POST with the next reply; records the tokens POSTed."""

    def __init__(self, *replies):
        self.replies = list(replies)
        self.tokens, self.gets = [], 0

    def __call__(self, _params, body):
        if not body:
            self.gets += 1
            return query_page(f"page{self.gets}")
        self.tokens.append(body["SYNCHRONIZER_TOKEN"])
        return self.replies.pop(0)


def test_week_levels_leave_out_the_adjustment_and_chain_tokens():
    site = Site(result_page("t1"), result_page(None), result_page("t2"))
    query = StockQuery(OfflineClient({"qryStock": site}))
    assert (query.first_date, query.dates) == ("20261016", ["20261016", "20261008"])
    week = query.week("2330", "20261008")
    assert [h.level for h in week.levels] == [1, 15, TOTAL]
    assert (week.total.people, week.total.shares, week.total.pct) == (3007088, 25932370067, Decimal("100.00"))
    query.week("2330", "20261008")  # 回應沒帶 token：重新載入查詢頁取得新的
    query.week("2330", "20261008")
    assert site.tokens == ["page1", "t1", "page2"] and site.gets == 2


def test_week_without_data_error_page_and_changed_table():
    site = Site(result_page("t1", rows=[], head=HEAD + NO_DATA),
                b'<html>\xe7\xb3\xbb\xe7\xb5\xb1\xe5\xbf\x99\xe7\xa2\x8c<input name="SYNCHRONIZER_TOKEN" value="t2" /></html>',
                result_page("t3", head=HEAD.replace("人數", "持有人數")),
                result_page("t4", rows=[("1", "1-999", "N/A", "287,438,824", "1.10")] + ROWS_20261008[1:]))
    query = StockQuery(OfflineClient({"qryStock": site}))
    assert query.week("9999", "20261016") is None
    with pytest.raises(UpstreamFormatError, match="無法解析"):
        query.week("2330", "20261016")
    with pytest.raises(UpstreamFormatError, match="人數"):
        query.week("2330", "20261016")
    with pytest.raises(UpstreamFormatError, match="數字格式"):
        query.week("2330", "20261016")


def test_changed_query_page_raises():
    with pytest.raises(UpstreamFormatError, match="頁面可能改版"):
        StockQuery(OfflineClient({"qryStock": lambda _params, _body: b"<html>changed</html>"}))
