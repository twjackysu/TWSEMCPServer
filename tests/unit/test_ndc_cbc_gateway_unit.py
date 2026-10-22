"""sources/ndc 與 sources/cbc 的單元測試（不打網路）。工具的月數、日期區間與幣別篩選見 test_free_sources_unit.py。

列取自真實檔案（國發會 6099 景氣指標與燈號、同時指標構成項目，6100 PMI；央行 BP01D01 第一天與 2026-09-30）；上游真實
格式由 tests/contract/test_tdcc_macro_api.py 驗證。
"""

import io
import zipfile
from datetime import date
from decimal import Decimal

import pytest

from sources.cbc.exchange_rates import exchange_rates
from sources.ndc.indicators import business_cycle, pmi
from tests.offline import OfflineClient
from utils.errors import UpstreamFormatError

pytestmark = pytest.mark.offline

SIGNAL_CSV = "\n".join([
    '"Date","領先指標綜合指數","領先指標不含趨勢指數","同時指標綜合指數","同時指標不含趨勢指數","落後指標綜合指數",'
    '"落後指標不含趨勢指數","景氣對策信號綜合分數","景氣對策信號"',
    "198201,12.28329451,100.3404372,13.11164891,107.1066347,13.08922753,106.9234786,-,-",
    "202312,94.50046308,99.13471995,91.33557843,95.8146866,96.44595408,101.1756757,22,黃藍 ",
    "202608,140.5879095,104.4086599,143.3642681,106.4711496,142.3356066,105.7072021,41,紅",
])
COINCIDENT_CSV = "\n".join([
    "Date,工業生產指數(Index2021=100),電力(企業)總用電量(十億度),製造業銷售量指數(Index2021=100),"
    "批發、零售及餐飲業營業額(十億元),工業及服務業加班工時(小時),海關出口值(十億元),機械及電機設備進口值(十億元)",
    "202608,145.97,,,2361.956097,,2655.817,1266.488",
])


def ndc_zip(**members):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("manifest.csv", "name,schema,description\n")
        for name, text in members.items():
            zf.writestr(name, "﻿" + text + "\n")
    return buf.getvalue()


def _ndc(body):
    return OfflineClient({"icon=.zip": body, "icon=.csv": body})


def test_business_cycle_columns_months_and_blank_values():
    table = business_cycle(_ndc(ndc_zip(**{"景氣指標與燈號.csv": SIGNAL_CSV})), "signal")
    assert table.columns[0] == "領先指標綜合指數" and table.columns[-2:] == ("景氣對策信號綜合分數", "景氣對策信號")
    first, yellow_blue, latest = table.rows
    assert (first.year, first.month, first.values[-2:]) == (1982, 1, (None, None))  # "-"
    assert yellow_blue.values[-1] == "黃藍"  # 尾端空白去掉
    assert (latest.year, latest.month, latest.values[-2:]) == (2026, 8, ("41", "紅"))
    coincident = business_cycle(_ndc(ndc_zip(**{"同時指標構成項目.csv": COINCIDENT_CSV})), "coincident")
    assert coincident.rows[0].values[:3] == ("145.97", None, None)  # "" 是尚未公布


def test_pmi_and_empty_csv():
    table = pmi(_ndc(("﻿Date,PMI,NMI\n201207,47.1,-\n202609,63.4,56.9\n").encode("utf-8")))
    assert table.columns == ("PMI", "NMI")
    assert [(r.year, r.month, r.values) for r in table.rows] == [(2012, 7, ("47.1", None)), (2026, 9, ("63.4", "56.9"))]
    assert pmi(_ndc("﻿Date,PMI,NMI\n".encode("utf-8"))) is None


def test_ndc_format_changes_raise():
    with pytest.raises(UpstreamFormatError, match="找不到 領先指標構成項目"):
        business_cycle(_ndc(ndc_zip(**{"景氣指標與燈號.csv": SIGNAL_CSV})), "leading")
    with pytest.raises(UpstreamFormatError, match="不是 zip"):
        business_cycle(_ndc(b"<html>moved</html>"), "signal")
    with pytest.raises(UpstreamFormatError, match="Date"):
        pmi(_ndc("年月,PMI,NMI\n202609,63.4,56.9\n".encode("utf-8")))
    with pytest.raises(UpstreamFormatError, match="YYYYMM"):
        pmi(_ndc("Date,PMI,NMI\n2026-09,63.4,56.9\n".encode("utf-8")))
    with pytest.raises(UpstreamFormatError, match="資料列有 2 欄"):
        pmi(_ndc("Date,PMI,NMI\n202609,63.4\n".encode("utf-8")))


TABLE1 = [{"data": "新台幣NTD/USD"}, {"data": "日圓JPY/USD"}, {"data": " 菲律賓披索PHP/USD"}, {"data": "歐元USD/EUR"},
          {"data": "馬克DEM/USD"}]
# 真實列只取上面五種幣別的欄
FIRST_DAY = ["19930105", "25.405", "125.25", "-", "-", "1.6255"]
LAST_DAY = ["20260930", "31.852", "156.89", "62.649", "1.1347", "-"]


def cbc_reply(rows=(FIRST_DAY, LAST_DAY), table1=TABLE1):
    return {"meta": {"title": "我國與主要貿易對手通貨對美元之匯率依期間", "last_updated": "2026-10-01"},
            "data": {"dataSets": [list(r) for r in rows], "structure": {"Table1": table1}}}


def _cbc(reply):
    return OfflineClient({"/API/DataAPI/Get": reply})


def test_exchange_rates_days_and_missing_quotes():
    table = exchange_rates(_cbc(cbc_reply()))
    assert table.currencies[2] == "菲律賓披索PHP/USD" and table.last_updated == "2026-10-01"
    first, last = table.days
    assert first.date == date(1993, 1, 5) and first.rates[3] is None  # 歐元 1993 是 "-"
    assert last.rates == (Decimal("31.852"), Decimal("156.89"), Decimal("62.649"), Decimal("1.1347"), None)
    assert exchange_rates(_cbc(cbc_reply(rows=()))) is None


def test_exchange_rates_format_changes_raise():
    with pytest.raises(UpstreamFormatError, match="結構已變更"):
        exchange_rates(_cbc({"meta": {}, "data": {"rows": []}}))
    with pytest.raises(UpstreamFormatError, match="對不上"):
        exchange_rates(_cbc(cbc_reply(rows=[LAST_DAY[:-1]])))
    with pytest.raises(UpstreamFormatError, match="日期格式"):
        exchange_rates(_cbc(cbc_reply(rows=[["2026-09-30"] + LAST_DAY[1:]])))
    with pytest.raises(UpstreamFormatError, match="匯率格式"):
        exchange_rates(_cbc(cbc_reply(rows=[LAST_DAY[:1] + ["N/A"] + LAST_DAY[2:]])))
