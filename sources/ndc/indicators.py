"""國發會 景氣指標及燈號 (data.gov.tw dataset 6099) and 臺灣採購經理人指數 (dataset 6100): monthly tables.

index.ndc.gov.tw sits behind a Cloudflare bot block, so these read the files NDC itself publishes on data.gov.tw,
through fixed ws.ndc.gov.tw download links taken from those dataset pages (tests/contract/test_tdcc_macro_api.py fails
if NDC re-points them):

- 6099: a zip of UTF-8 (BOM) CSVs, one per table (``CYCLE_TABLES``), plus manifest.csv and a schema-*.csv per table.
  Monthly from 198201.
- 6100: one CSV, ``Date,PMI,NMI``, monthly from 201207.

Every table is ``Date`` (YYYYMM) followed by its series, oldest month first::

    Date,領先指標綜合指數,…,景氣對策信號綜合分數,景氣對策信號
    198201,12.28329451,…,-,-
    202608,140.5879095,…,41,紅

A value is a number, the 燈號 colour (紅, 黃紅, 綠, 黃藍 — printed with a trailing space —, 藍), "-" or "" (the
latest month's late series are "").
"""

import csv
import io
import zipfile
from dataclasses import dataclass
from typing import List, Literal, Optional, Tuple

from utils.api_client import TWSEAPIClient
from utils.errors import UpstreamFormatError

from ..columns import column_index

# data.gov.tw/dataset/6099 景氣指標及燈號 (zip of CSVs)
BUSINESS_CYCLE_ZIP_URL = (
    "https://ws.ndc.gov.tw/Download.ashx?u=LzAwMS9hZG1pbmlzdHJhdG9yLzEwL3JlbGZpbGUvNTc4MS82Mzky"
    "L2VhMjM1YmQ5LWQwNTItNGE2OS1hYmZjLWQ1Yzc4NWQzZDBlMi56aXA%3d&n=5pmv5rCj5oyH5qiZ5Y%2bK54eI6JmfLnppcA%3d%3d&icon=.zip"
)
# data.gov.tw/dataset/6100 臺灣採購經理人指數 (CSV: Date,PMI,NMI)
PMI_CSV_URL = (
    "https://ws.ndc.gov.tw/Download.ashx?u=LzAwMS9hZG1pbmlzdHJhdG9yLzEwL3JlbGZpbGUvNTc4MS82Mzkx"
    "L2JmOGE0ZWI3LTEwZmUtNGZhMC1iNjQ2LTMwZTg5MGQwMjE4YS5jc3Y%3d&n=6Ie654Gj5o6h6LO857aT55CG5Lq65oyH5pW4KHBtaeWPim5taSkuY3N2&icon=.csv"
)
# Monthly data; both files are whole-history downloads.
CACHE_TTL = 6 * 3600

# CSV files inside the 6099 zip, by the name the tool exposes.
Table = Literal["signal", "signal_components", "leading", "coincident", "lagging"]  # CYCLE_TABLES
CYCLE_TABLES = {
    "signal": "景氣指標與燈號.csv",
    "signal_components": "景氣對策信號構成項目.csv",
    "leading": "領先指標構成項目.csv",
    "coincident": "同時指標構成項目.csv",
    "lagging": "落後指標構成項目.csv",
}
DATE = "Date"


@dataclass(frozen=True)
class MonthRow:
    year: int                          # 西元, from Date
    month: int
    values: Tuple[Optional[str], ...]  # one per MonthlyTable.columns, as published without padding; None for "-" or ""


@dataclass(frozen=True)
class MonthlyTable:
    columns: Tuple[str, ...]  # the series after Date, as published ("景氣對策信號綜合分數", "PMI")
    rows: List[MonthRow]      # oldest month first


def _monthly_table(text: str, source: str) -> Optional[MonthlyTable]:
    rows = list(csv.reader(io.StringIO(text)))
    if len(rows) < 2:
        return None
    header = [c.strip() for c in rows[0]]
    date_col = column_index(header, (DATE,), source)[DATE]
    months = []
    for r in rows[1:]:
        if not any(c.strip() for c in r):
            continue
        if len(r) != len(header):
            raise UpstreamFormatError(f"{source} 資料列有 {len(r)} 欄，表頭有 {len(header)} 欄：{r}")
        ym = r[date_col].strip()
        if len(ym) != 6 or not ym.isdigit():
            raise UpstreamFormatError(f"{source} 的 Date 不再是 YYYYMM：{r}")
        values = tuple(None if v.strip() in ("", "-") else v.strip() for i, v in enumerate(r) if i != date_col)
        months.append(MonthRow(year=int(ym[:4]), month=int(ym[4:]), values=values))
    return MonthlyTable(columns=tuple(h for i, h in enumerate(header) if i != date_col), rows=months)


def business_cycle(client: TWSEAPIClient, table: Table) -> Optional[MonthlyTable]:
    """One 6099 table (``CYCLE_TABLES``), or None when its CSV has no rows. Raises ``UpstreamFormatError`` when
    the download is not a zip, the CSV is not in it, or its layout changed."""
    body = client.fetch_bytes(BUSINESS_CYCLE_ZIP_URL, timeout=60, cache_ttl=CACHE_TTL)
    filename = CYCLE_TABLES[table]
    try:
        with zipfile.ZipFile(io.BytesIO(body)) as zf:
            member = next((i for i in zf.infolist() if i.filename.rsplit("/", 1)[-1] == filename), None)
            if member is None:
                raise UpstreamFormatError(f"國發會景氣指標壓縮檔內找不到 {filename}")
            text = zf.read(member).decode("utf-8-sig")
    except zipfile.BadZipFile:
        raise UpstreamFormatError(f"國發會景氣指標下載內容不是 zip（連結可能已失效）：{body[:80]!r}") from None
    return _monthly_table(text, filename)


def pmi(client: TWSEAPIClient) -> Optional[MonthlyTable]:
    """The 6100 PMI / NMI table, or None when the CSV has no rows. Raises ``UpstreamFormatError`` if its layout
    changed."""
    body = client.fetch_bytes(PMI_CSV_URL, timeout=60, cache_ttl=CACHE_TTL)
    return _monthly_table(body.decode("utf-8-sig"), "PMI CSV")
