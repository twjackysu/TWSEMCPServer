"""sources/twse/t86.py、sources/tpex/insti_daily.py 的單元測試（不打網路）：兩個市場都轉成 InstitutionalFlow。

上游真實格式由 tests/contract/test_twse_institutional_api.py、test_otc_history_api.py 驗證。
"""

import pytest

from sources.institutional import Trades
from sources.tpex.insti_daily import tpex_flows
from sources.twse.t86 import t86_flows
from tests.offline import OfflineClient
from utils.errors import UpstreamFormatError

pytestmark = pytest.mark.offline


def _g(who, suffix=""):
    return [f"{who}{k}股數{suffix}" for k in ("買進", "賣出", "買賣超")]


# T86 的三種欄位格式（2012 起 12 欄 → 自營商拆自行／避險 16 欄 → 外資拆外資自營商 19 欄）
T86_19 = (["證券代號", "證券名稱"] + _g("外陸資", "(不含外資自營商)") + _g("外資自營商") + _g("投信")
          + ["自營商買賣超股數"] + _g("自營商", "(自行買賣)") + _g("自營商", "(避險)") + ["三大法人買賣超股數"])
T86_16 = (["證券代號", "證券名稱"] + _g("外資") + _g("投信")
          + ["自營商買賣超股數"] + _g("自營商", "(自行買賣)") + _g("自營商", "(避險)") + ["三大法人買賣超股數"])
T86_12 = ["證券代號", "證券名稱"] + _g("外資") + _g("投信") + ["自營商買賣超股數", "自營商買進股數", "自營商賣出股數",
                                                       "三大法人買賣超股數"]
ROW_19 = ["2330", "台積電          ", "1,000", "300", "700", "50", "0", "50", "20", "30", "-10",
          "-5", "10", "12", "-2", "0", "3", "-3", "735"]
ROW_16 = ["2330", "台積電          ", "1,050", "300", "750", "20", "30", "-10",
          "-5", "10", "12", "-2", "0", "3", "-3", "735"]
ROW_12 = ["2330", "台積電          ", "1,050", "300", "750", "20", "30", "-10", "-5", "10", "15", "735"]


def _t86(fields, rows, stat="OK"):
    return OfflineClient({"/fund/T86": {"stat": stat, "date": "20260930", "title": "115年09月30日 三大法人買賣超日報",
                                        "fields": fields, "data": rows}})


def test_t86_current_layout_splits_foreign_and_dealer():
    day = t86_flows(_t86(T86_19, [ROW_19]), "ALLBUT0999", "20260930")
    assert (day.date, day.title) == ("20260930", "115年09月30日 三大法人買賣超日報")
    f = day.flows[0]
    assert (f.code, f.name) == ("2330", "台積電")  # 名稱去掉補位空白
    assert f.foreign_ex_dealer == Trades(1000, 300, 700) and f.foreign_dealer == Trades(50, 0, 50)
    assert f.foreign == Trades(1050, 300, 750)  # 外資合計＝兩者相加
    assert f.dealer == Trades(None, None, -5)    # 自營商合計只公布買賣超
    assert (f.dealer_self, f.dealer_hedge, f.trust, f.total_net) == (Trades(10, 12, -2), Trades(0, 3, -3), Trades(20, 30, -10), 735)
    assert [f.net(k) for k in ("total", "foreign", "trust", "dealer")] == [735, 750, -10, -5]


def test_t86_older_layouts_are_read_by_name():
    f16 = t86_flows(_t86(T86_16, [ROW_16]), "ALL", "20171003").flows[0]
    assert f16.foreign == Trades(1050, 300, 750) and f16.foreign_ex_dealer is None and f16.foreign_dealer is None
    assert f16.dealer_self == Trades(10, 12, -2) and f16.dealer == Trades(None, None, -5)
    f12 = t86_flows(_t86(T86_12, [ROW_12]), "ALL", "20141003").flows[0]
    assert f12.dealer == Trades(10, 15, -5) and f12.dealer_self is None and f12.dealer_hedge is None
    assert [f12.net(k) for k in ("total", "foreign", "trust", "dealer")] == [735, 750, -10, -5]


def test_t86_columns_are_found_by_name():
    order = list(reversed(range(len(T86_19))))
    shuffled = t86_flows(_t86([T86_19[i] for i in order], [[ROW_19[i] for i in order]]))
    assert shuffled.flows == t86_flows(_t86(T86_19, [ROW_19])).flows


@pytest.mark.parametrize("fields,row,match", [
    ([f if f != "投信買賣超股數" else "投信淨買股數" for f in T86_19], ROW_19, "投信買賣超股數"),
    (T86_19, ROW_19[:-1], "18 欄"),
    (T86_19, ROW_19[:18] + ["--"], "三大法人買賣超股數"),
])
def test_t86_layout_changes_are_errors(fields, row, match):
    with pytest.raises(UpstreamFormatError, match=match):
        t86_flows(_t86(fields, [row]))


def test_t86_no_data_is_none_and_latest_day_omits_date():
    seen = []

    def route(params, _body):
        seen.append(dict(params))
        return {"stat": "很抱歉，沒有符合條件的資料!", "total": 0}

    assert t86_flows(OfflineClient({"/fund/T86": route}), "24") is None
    assert seen == [{"response": "json", "selectType": "24"}]


# ---------- TPEx insti/dailyTrade ----------

TPEX_FIELDS = ["代號", "名稱"] + ["買進股數", "賣出股數", "買賣超股數"] * 7 + ["三大法人買賣超股數合計"]
# 外資不含自營商、外資自營商、外資合計、投信、自營商自行、自營商避險、自營商合計（各 買/賣/超），三大法人合計
TPEX_ROW = ["6488", "環球晶", "1,000", "300", "700", "50", "0", "50", "1,050", "300", "750", "20", "30", "-10",
            "10", "12", "-2", "0", "3", "-3", "10", "15", "-5", "735"]


def _tpex(rows, fields=TPEX_FIELDS, seen=None):
    def route(params, _body):
        if seen is not None:
            seen.append(dict(params))
        return {"date": "20260930", "stat": "ok", "tables": [{"subtitle": "115年09月30日 三大法人日交易資訊",
                                                              "fields": fields, "data": rows}, {}]}
    return OfflineClient({"/insti/dailyTrade": route})


def test_tpex_groups_map_to_the_same_record():
    seen = []
    day = tpex_flows(_tpex([TPEX_ROW], seen=seen), "EW", "20260930")
    assert seen == [{"type": "Daily", "sect": "EW", "response": "json", "date": "2026/09/30"}]
    f = day.flows[0]
    assert (day.date, f.code, f.name) == ("20260930", "6488", "環球晶")
    assert (f.foreign_ex_dealer, f.foreign_dealer, f.foreign) == (Trades(1000, 300, 700), Trades(50, 0, 50), Trades(1050, 300, 750))
    assert (f.trust, f.dealer_self, f.dealer_hedge, f.dealer) == (Trades(20, 30, -10), Trades(10, 12, -2), Trades(0, 3, -3), Trades(10, 15, -5))
    assert [f.net(k) for k in ("total", "foreign", "trust", "dealer")] == [735, 750, -10, -5]


def test_tpex_group_order_is_checked_by_the_sums():
    swapped = TPEX_ROW[:]
    swapped[11:14], swapped[14:17] = TPEX_ROW[14:17], TPEX_ROW[11:14]  # 投信與自營商自行互換
    with pytest.raises(UpstreamFormatError, match="加總不符"):
        tpex_flows(_tpex([swapped]))


def test_tpex_renamed_field_is_an_error():
    with pytest.raises(UpstreamFormatError, match="欄位已變更"):
        tpex_flows(_tpex([TPEX_ROW], TPEX_FIELDS[:-1] + ["三大法人買賣超合計"]))


def test_tpex_empty_table_is_none_and_missing_tables_an_error():
    seen = []
    assert tpex_flows(_tpex([], seen=seen)) is None
    assert seen == [{"type": "Daily", "sect": "EW", "response": "json"}]
    with pytest.raises(UpstreamFormatError, match="tables"):
        tpex_flows(OfflineClient({"/insti/dailyTrade": {"stat": "ok"}}))
