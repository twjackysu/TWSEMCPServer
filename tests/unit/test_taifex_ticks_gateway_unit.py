"""sources/taifex/ticks.py 的單元測試（不打網路）。分K、時段與工具輸出見 test_taifex_intraday_unit.py。

列取自期交所真實檔案（Daily_2026_09_08.zip：夜盤開盤、跨午夜、日盤開盤、價差單、週契約）；上游真實格式由
tests/contract/test_taifex_history_api.py::TestFuturesTickDownloadAPI 驗證。
"""

import io
import zipfile

import pytest

from sources.taifex.ticks import Trade, products, trades, trading_days
from tests.offline import OfflineClient
from utils.errors import UpstreamFormatError

pytestmark = pytest.mark.offline

HEADER = "成交日期,商品代號,到期月份(週別),成交時間,成交價格,成交數量(B+S),近月價格,遠月價格,開盤集合競價 "
ROWS = [
    "20260907,TX     ,202609     ,150000,47513,56,-,-,*",
    "20260907,TX     ,202609/202610,150000,188,4,47520,47708, ",
    "20260907,MTX    ,202609W2     ,150000,47361,4,-,-, ",
    "20260908,TX     ,202609     ,000000,47319,2,-,-, ",
    "20260908,TX     ,202609     ,084500,47480,272,-,-,*",
]
PAGE = ('<a href="/file/taifex/Dailydownload/DailydownloadCSV/Daily_2026_09_08.zip">x</a>'
        '<a href="/file/taifex/Dailydownload/Dailydownload/Daily_2026_09_09.zip">rpt</a>'
        '<a href="/file/taifex/Dailydownload/DailydownloadCSV/Daily_2026_09_09.zip">x</a>').encode("utf-8")


def tick_zip(*lines, header=HEADER):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("Daily_2026_09_08.csv", ("\r\n".join((header,) + lines) + "\r\n").encode("cp950"))
    return buf.getvalue()


def _client(body):
    return OfflineClient({"dlFutPrevious30DaysSalesData": PAGE, "Daily_2026_09_08.zip": body})


def test_trades_of_one_contract_without_spreads():
    assert trades(_client(tick_zip(*ROWS)), "20260908", "TX") == [
        Trade("20260907", "202609", 150000, 47513.0, 56),
        Trade("20260908", "202609", 0, 47319.0, 2),
        Trade("20260908", "202609", 84500, 47480.0, 272),
    ]
    assert trades(_client(tick_zip(*ROWS)), "20260908", "MTX")[0].month == "202609W2"


def test_trading_days_products_and_format_changes():
    client = _client(tick_zip(*ROWS))
    assert trading_days(client) == ["20260909", "20260908"]  # Dailydownload/ 的固定寬度報表不算
    assert products(client, "20260908") == ["MTX", "TX"]
    with pytest.raises(UpstreamFormatError, match="找不到任何檔案連結"):
        trading_days(OfflineClient({"dlFutPrevious30DaysSalesData": b"<html>changed</html>"}))
    with pytest.raises(UpstreamFormatError, match="成交價格"):
        trades(_client(tick_zip(*ROWS, header=HEADER.replace("成交價格", "價格"))), "20260908", "TX")
    with pytest.raises(UpstreamFormatError, match="格式已變更"):
        trades(_client(tick_zip("20260908,TX     ,202609     ,084500,N/A,272,-,-,*")), "20260908", "TX")
    with pytest.raises(UpstreamFormatError, match="欄數不足"):
        trades(_client(tick_zip("20260908,TX     ,202609")), "20260908", "TX")
    with pytest.raises(UpstreamFormatError, match="不是 zip"):
        trades(_client(b"<html>not found</html>"), "20260908", "TX")
