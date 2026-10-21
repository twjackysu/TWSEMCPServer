"""sources/twse/mi_index.py 的單元測試（不打網路）。

上游真實格式由 tests/contract/test_history_tier1_api.py、test_history_tier3_api.py、test_screening_api.py 驗證。
"""

from decimal import Decimal

import pytest

from sources.twse.mi_index import index_quotes, stock_quotes
from tests.offline import OfflineClient
from utils.errors import UpstreamFormatError

pytestmark = pytest.mark.offline

QUOTE_FIELDS = ["證券代號", "證券名稱", "成交股數", "成交筆數", "成交金額", "開盤價", "最高價", "最低價", "收盤價",
                "漲跌(+/-)", "漲跌價差", "最後揭示買價", "最後揭示買量", "最後揭示賣價", "最後揭示賣量", "本益比"]
QUOTES = [
    ["2330", "台積電", "34,282,491", "83,797", "85,388,527,300", "2,495.00", "2,510.00", "2,480.00", "2,480.00",
     "<p style= color:red>+</p>", "5.00", "2,480.00", "1", "2,485.00", "2", "28.75"],
    ["1101", "台泥", "1,000", "1", "23,000", "--", "--", "--", "--", "<p> </p>", "0.00", "--", "0", "--", "0", ""],
    ["2002", "中鋼", "2,000", "2", "40,000", "20.00", "20.10", "19.90", "20.00", "<p style= color:green>-</p>", "0.15",
     "20.00", "1", "20.05", "1", "0.00"],
    ["0056", "元大高股息", "1,000", "1", "35,000", "35.00", "35.00", "35.00", "35.00", "<p>X</p>", "0.00",
     "35.00", "1", "35.05", "1", "0.00"],
]
QUOTE_REPLY = {"stat": "OK", "date": "20260930", "tables": [
    {"title": "115年09月30日 價格指數(臺灣證券交易所)", "fields": ["指數", "收盤指數"], "data": [["寶島股價指數", "1"]]},
    {"title": "115年09月30日 每日收盤行情(全部(不含權證、牛熊證、可展延牛熊證))", "fields": QUOTE_FIELDS, "data": QUOTES},
]}
IND_FIELDS = ["指數", "收盤指數", "漲跌(+/-)", "漲跌點數", "漲跌百分比(%)", "特殊處理註記"]
IND_REPLY = {"stat": "OK", "date": "20260930", "tables": [
    {"title": "115年09月30日 價格指數(臺灣證券交易所)", "fields": IND_FIELDS, "data": [
        ["發行量加權股價指數", "26,000.50", "<p style ='color:red'>+</p>", "120.30", "0.46", ""],
        ["半導體類指數", "1,491.44", "<p style ='color:green'>-</p>", "3.37", "-0.23", "註"]]},
    {"title": "報酬指數(跨市場)", "fields": ["報酬指數"] + IND_FIELDS[1:], "data": [
        ["臺灣生技報酬指數", "4,965.74", "<p style ='color:red'>+</p>", "87.69", "1.80", ""]]},
    {"title": None, "data": []},
]}


def _client(reply):
    return OfflineClient({"/afterTrading/MI_INDEX": reply})


def test_quote_table_is_found_by_title_and_typed():
    table = stock_quotes(_client(QUOTE_REPLY), "ALLBUT0999", "20260930")
    assert table.date == "20260930" and table.group == "全部(不含權證、牛熊證、可展延牛熊證)"
    tsmc, untraded, down, exright = table.quotes
    assert (tsmc.code, tsmc.name, tsmc.volume, tsmc.transactions, tsmc.value) == ("2330", "台積電", 34282491, 83797, 85388527300)
    assert str(tsmc.close) == "2480.00" and tsmc.pe == Decimal("28.75")
    assert (tsmc.direction, tsmc.change) == ("+", Decimal("5.00"))
    assert (untraded.close, untraded.pe, untraded.direction, untraded.change) == (None, None, "", Decimal("0.00"))
    assert (down.direction, down.change, down.change_points) == ("-", Decimal("-0.15"), Decimal("0.15"))
    assert exright.direction == "X" and exright.change == Decimal("0.00")


def test_industry_table_names_its_group():
    reply = {"stat": "OK", "date": "20260930", "tables": [
        {"title": "115年09月30日 每日收盤行情(半導體業)", "fields": QUOTE_FIELDS, "data": QUOTES[:1]}]}
    assert stock_quotes(_client(reply), "24").group == "半導體業"


def test_columns_are_found_by_name():
    order = list(reversed(range(len(QUOTE_FIELDS))))
    table = dict(QUOTE_REPLY["tables"][1], fields=[QUOTE_FIELDS[i] for i in order], data=[[r[i] for i in order] for r in QUOTES])
    shuffled = stock_quotes(_client({**QUOTE_REPLY, "tables": [table]}))
    assert shuffled.quotes == stock_quotes(_client(QUOTE_REPLY)).quotes


def test_renamed_quote_column_is_an_error():
    table = dict(QUOTE_REPLY["tables"][1], fields=["代號"] + QUOTE_FIELDS[1:])
    with pytest.raises(UpstreamFormatError, match="證券代號"):
        stock_quotes(_client({**QUOTE_REPLY, "tables": [table]}))


def test_no_trading_day_is_none():
    assert stock_quotes(_client({"stat": "很抱歉，沒有符合條件的資料!"})) is None
    assert index_quotes(_client({"stat": "很抱歉，沒有符合條件的資料!"})) is None


def test_index_board_keeps_titled_tables_and_signs():
    board = index_quotes(_client(IND_REPLY), "20260930")
    assert board.date == "20260930" and [t.title for t in board.tables] == ["115年09月30日 價格指數(臺灣證券交易所)", "報酬指數(跨市場)"]
    taiex, semi = board.tables[0].quotes
    assert (taiex.name, str(taiex.close), taiex.change, taiex.change_pct) == ("發行量加權股價指數", "26000.50", Decimal("120.30"), Decimal("0.46"))
    assert (semi.direction, semi.change, semi.change_pct, semi.note) == ("-", Decimal("-3.37"), Decimal("-0.23"), "註")
    assert board.tables[1].quotes[0].name == "臺灣生技報酬指數"  # name column is 報酬指數 there


def test_latest_day_omits_date_and_past_day_sends_it():
    seen = []

    def route(params, _body):
        seen.append(dict(params))
        return QUOTE_REPLY

    stock_quotes(_client(route))
    stock_quotes(_client(route), "24", "20260930")
    assert seen == [{"response": "json", "type": "ALLBUT0999"}, {"response": "json", "type": "24", "date": "20260930"}]
