"""sources/twse/bwibbu_d.py 的單元測試（不打網路）。

上游真實格式由 tests/contract/test_history_api.py、test_screening_api.py 驗證。
"""

from decimal import Decimal

import pytest

from sources.twse.bwibbu_d import valuation_ratios
from tests.offline import OfflineClient
from utils.errors import UpstreamFormatError

pytestmark = pytest.mark.offline

FIELDS = ["證券代號", "證券名稱", "收盤價", "殖利率(%)", "股利年度", "本益比", "股價淨值比", "財報年/季"]
ROWS = [
    ["2330", "台積電", "2,480.00", "0.89", 114, "28.75", "10.00", "115/2"],  # 股利年度 是 JSON 數字
    ["1101", "台泥", "26.30", "3.04", 114, "-", "0.85", "115/2"],            # 虧損：本益比 "-"
]
REPLY = {"stat": "OK", "date": "20260930", "title": "115年09月30日 個股日本益比、殖利率及股價淨值比",
         "fields": FIELDS, "data": ROWS}


def _client(reply):
    return OfflineClient({"/afterTrading/BWIBBU_d": reply})


def test_rows_are_typed():
    report = valuation_ratios(_client(REPLY), "20260930")
    assert report.found and (report.date, report.title) == ("20260930", "115年09月30日 個股日本益比、殖利率及股價淨值比")
    tsmc, loss = report.valuations
    assert (tsmc.code, tsmc.name, str(tsmc.close), tsmc.dividend_yield) == ("2330", "台積電", "2480.00", Decimal("0.89"))
    assert (tsmc.pe, tsmc.pb, tsmc.dividend_year, tsmc.fiscal) == (Decimal("28.75"), Decimal("10.00"), "114", "115/2")
    assert loss.pe is None


def test_columns_are_found_by_name():
    order = list(reversed(range(len(FIELDS))))
    shuffled = {**REPLY, "fields": [FIELDS[i] for i in order], "data": [[r[i] for i in order] for r in ROWS]}
    assert valuation_ratios(_client(shuffled)) == valuation_ratios(_client(REPLY))


def test_renamed_column_is_an_error():
    with pytest.raises(UpstreamFormatError, match="本益比"):
        valuation_ratios(_client({**REPLY, "fields": [f if f != "本益比" else "PER" for f in FIELDS]}))


def test_nothing_to_report_keeps_twse_reason_and_date():
    report = valuation_ratios(_client({"stat": "很抱歉，沒有符合條件的資料!", "date": "20261004"}), "20261004")
    assert (report.found, report.stat, report.date, report.valuations) == (False, "很抱歉，沒有符合條件的資料!", "20261004", [])


def test_latest_day_omits_date_and_past_day_sends_it():
    seen = []

    def route(params, _body):
        seen.append(dict(params))
        return REPLY

    valuation_ratios(_client(route))
    valuation_ratios(_client(route), "20260930")
    assert seen == [{"response": "json", "selectType": "ALL"},
                    {"response": "json", "selectType": "ALL", "date": "20260930"}]
