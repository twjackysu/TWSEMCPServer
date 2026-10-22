"""TAIFEX 期貨每筆成交資料: every futures trade of a trading day, for the last 30 trading days.

``GET www.taifex.com.tw/cht/3/dlFutPrevious30DaysSalesData`` links one zip per trading day,
``/file/taifex/Dailydownload/DailydownloadCSV/Daily_YYYY_MM_DD.zip`` (the ``Dailydownload/`` twins are fixed-width
reports). Each zip (~2.5 MB) holds one cp950 CSV of ~600,000–900,000 trades (~45 MB)::

    成交日期,商品代號,到期月份(週別),成交時間,成交價格,成交數量(B+S),近月價格,遠月價格,開盤集合競價
    20261021,BRF    ,202612     ,202827,3521,22,-,-,
    …
    20261022,ZFF    ,202611     ,134414,3751.8,2,-,-,

A trading day's file starts with its night session (from 15:00 the evening before, dated that evening, past midnight),
then the day session (08:45–13:45); before the day session opens the newest file holds only the night session. Codes
and months are space-padded; months are "202611" or weekly "202610W4", and a calendar spread's is "202610/202611"
(its price is the spread, possibly negative). 成交數量(B+S) counts both sides of each trade.
"""

import io
import re
import zipfile
from typing import List, NamedTuple

from utils.api_client import TWSEAPIClient
from utils.errors import UpstreamFormatError
from utils.taifex import TAIFEX_DOWNLOAD_BASE, TAIFEX_HEADERS

from ..columns import column_index

PAGE_URL = f"{TAIFEX_DOWNLOAD_BASE}/dlFutPrevious30DaysSalesData"
ZIP_BASE = "https://www.taifex.com.tw/file/taifex/Dailydownload/DailydownloadCSV"
_ZIP_RE = re.compile(r"DailydownloadCSV/Daily_(\d{4})_(\d{2})_(\d{2})\.zip")
# The page lists a new day once per evening; a trading day's file never changes.
PAGE_CACHE_TTL = 600
ZIP_CACHE_TTL = 6 * 3600
SOURCE = "期交所每筆成交 CSV"
FIELDS = ("成交日期", "商品代號", "到期月份(週別)", "成交時間", "成交價格", "成交數量(B+S)")


class Trade(NamedTuple):
    """One trade. A NamedTuple rather than a dataclass: a contract has ~80,000 of them a day."""
    date: str     # 成交日期 YYYYMMDD (a night trade after midnight carries the next date)
    month: str    # 到期月份(週別) without its padding ("202611", "202610W4")
    time: int     # 成交時間 HHMMSS as a number (84500 = 08:45:00)
    price: float  # 成交價格
    volume: int   # 成交數量(B+S): both sides, so contracts = volume / 2


def trading_days(client: TWSEAPIClient) -> List[str]:
    """The YYYYMMDD days the download page offers, newest first. Raises ``UpstreamFormatError`` when it links
    none (a redesigned page)."""
    page = client.fetch_bytes(PAGE_URL, headers=TAIFEX_HEADERS, timeout=60, cache_ttl=PAGE_CACHE_TTL)
    days = sorted({"".join(m) for m in _ZIP_RE.findall(page.decode("utf-8", errors="replace"))}, reverse=True)
    if not days:
        raise UpstreamFormatError("期交所每筆成交下載頁找不到任何檔案連結，頁面可能改版")
    return days


def _rows(client: TWSEAPIClient, day: str):
    """(column positions, data lines) of ``day``'s CSV (the zip's only file)."""
    url = f"{ZIP_BASE}/Daily_{day[:4]}_{day[4:6]}_{day[6:]}.zip"
    body = client.fetch_bytes(url, headers=TAIFEX_HEADERS, timeout=120, cache_ttl=ZIP_CACHE_TTL)
    try:
        with zipfile.ZipFile(io.BytesIO(body)) as zf:
            text = zf.read(zf.namelist()[0]).decode("cp950", errors="replace")
    except (zipfile.BadZipFile, IndexError):
        raise UpstreamFormatError(f"期交所每筆成交 {day} 的下載內容不是 zip 或是空的") from None
    lines = text.splitlines()
    if not lines:
        raise UpstreamFormatError(f"{SOURCE} {day} 是空檔案")
    return column_index(lines[0].split(","), FIELDS, SOURCE), lines[1:]


def trades(client: TWSEAPIClient, day: str, contract: str) -> List[Trade]:
    """``contract``'s single-month trades on trading day ``day`` (one of ``trading_days``), in file order (night
    session, then day session); calendar spreads are left out. Raises ``UpstreamFormatError`` if the header changed
    or one of its rows does not read as numbers."""
    col, lines = _rows(client, day)
    code, month, hhmmss, price, volume = (col[f] for f in FIELDS[1:])
    width = max(col.values()) + 1
    out: List[Trade] = []
    for line in lines:
        cells = line.split(",")
        if len(cells) < width:
            if line.strip():
                raise UpstreamFormatError(f"{SOURCE} {day} 資料列欄數不足：{line[:120]}")
            continue
        if cells[code].strip() != contract or "/" in cells[month]:
            continue
        try:
            out.append(Trade(cells[col["成交日期"]].strip(), cells[month].strip(), int(cells[hhmmss]),
                             float(cells[price]), int(cells[volume])))
        except ValueError:
            raise UpstreamFormatError(f"{SOURCE} {day} 成交時間／價格／數量格式已變更：{line[:120]}") from None
    return out


def products(client: TWSEAPIClient, day: str) -> List[str]:
    """Every product code traded on ``day``, sorted."""
    col, lines = _rows(client, day)
    code = col["商品代號"]
    return sorted({cells[code].strip() for cells in (line.split(",") for line in lines) if len(cells) > code})
