"""TDCC open data 1-5: 集保戶股權分散表 — every security's holding-size distribution for the latest week.

``GET https://opendata.tdcc.com.tw/getOD.ashx?id=1-5``: one ~2.3 MB CSV (UTF-8 with BOM), about 70,000 rows,
17 per security (持股分級 1–17, see ``sources.tdcc.levels``)::

    資料日期,證券代號,持股分級,人數,股數,占集保庫存數比例%
    20261008,2330  ,1,2459344,287438824,1.10
    …
    20261008,2330  ,17,3007088,25932370067,100.00

證券代號 is padded with spaces to six characters; numbers have no separators. Only the latest week is served.
"""

import csv
import io
from dataclasses import dataclass
from datetime import date, datetime
from typing import List, Optional

from utils.api_client import TWSEAPIClient
from utils.errors import UpstreamFormatError
from utils.parse import decimal_or_none, int_or_none

from ..columns import column_index
from .levels import LevelHolding

URL = "https://opendata.tdcc.com.tw/getOD.ashx?id=1-5"
# The whole market in one file: without a cache every single-stock lookup re-downloads it.
CACHE_TTL = 3600
SOURCE = "集保股權分散表 CSV"
FIELDS = ("資料日期", "證券代號", "持股分級", "人數", "股數", "占集保庫存數比例%")


@dataclass(frozen=True)
class Distribution:
    date: date                  # 資料日期
    levels: List[LevelHolding]  # in the file's order (持股分級 1–17)


def latest_distribution(client: TWSEAPIClient, code: str) -> Optional[Distribution]:
    """``code``'s distribution in the latest week's file, or None when the file has no rows for it. Raises
    ``UpstreamFormatError`` on a changed header or a row that does not read as numbers."""
    body = client.fetch_bytes(URL, timeout=60, cache_ttl=CACHE_TTL)
    rows = list(csv.reader(io.StringIO(body.decode("utf-8-sig"))))
    if not rows:
        raise UpstreamFormatError(f"{SOURCE} 是空檔案")
    col = column_index(rows[0], FIELDS, SOURCE)
    width = len(rows[0])
    day: Optional[date] = None
    levels: List[LevelHolding] = []
    for r in rows[1:]:
        if not r:
            continue
        if len(r) != width:
            raise UpstreamFormatError(f"{SOURCE} 資料列有 {len(r)} 欄，表頭有 {width} 欄：{r}")
        if r[col["證券代號"]].strip() != code:
            continue
        level, people, shares = (int_or_none(r[col[f]]) for f in ("持股分級", "人數", "股數"))
        pct = decimal_or_none(r[col["占集保庫存數比例%"]])
        if level is None or people is None or shares is None or pct is None:
            raise UpstreamFormatError(f"{SOURCE} 數字格式已變更：{r}")
        try:
            day = datetime.strptime(r[col["資料日期"]].strip(), "%Y%m%d").date()
        except ValueError:
            raise UpstreamFormatError(f"{SOURCE} 資料日期格式已變更：{r}") from None
        levels.append(LevelHolding(level=level, people=people, shares=shares, pct=pct))
    if day is None:
        return None
    return Distribution(date=day, levels=levels)
