"""What every TAIFEX download-page gateway shares: post the page's form for a date range, decode the
cp950 CSV, find the columns by their header names.

A download page (``www.taifex.com.tw/cht/3/<page>``) answers a POST of ``queryStartDate`` /
``queryEndDate`` (YYYY/MM/DD) plus page-specific fields with a CSV whose first line names the
columns. A day or range without data, or a rejected query, is an HTML page instead
(``utils.taifex.decode_and_parse_csv`` turns that into None). Some pages end the header with a
trailing comma their rows lack, so a row may be one cell shorter than the header.

A gateway built on this module looks its columns up by name (``download_table``), turns each row
into a frozen dataclass, and parses numbers with ``number`` / ``count``: TAIFEX prints no thousands
separators and "-" where there is no value.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Dict, List, Optional, Sequence, Tuple

from utils.api_client import TWSEAPIClient
from utils.errors import UpstreamFormatError
from utils.parse import decimal_or_none, int_or_none
from utils.taifex import TAIFEX_CACHE_TTL, TAIFEX_HEADERS, decode_and_parse_csv, download_form

from ..columns import column_index


def download_table(client: TWSEAPIClient, url: str, source: str, required: Sequence[str],
                   start: date, end: date, **form: str) -> Optional[Tuple[Dict[str, int], List[List[str]]]]:
    """(column positions by name, data rows) of ``url`` for ``start``..``end``, or None when TAIFEX has
    no data for it. Raises ``UpstreamFormatError`` if a ``required`` column is gone or a row is too
    short to hold them."""
    body = client.fetch_bytes(url, method="POST", headers=TAIFEX_HEADERS, data=download_form(start, end, **form),
                              cache_ttl=TAIFEX_CACHE_TTL)
    parsed = decode_and_parse_csv(body)
    if parsed is None:
        return None
    header, rows = parsed
    col = column_index([h.strip() for h in header], required, source)
    width = max(col.values()) + 1
    for r in rows:
        if len(r) < width:
            raise UpstreamFormatError(f"{source} 資料列只有 {len(r)} 欄，讀不到第 {width} 欄：{r}")
    return col, rows


def trade_date(value: str, source: str) -> date:
    """A row's 交易日期 / 日期, published as YYYY/MM/DD."""
    try:
        return datetime.strptime(value.strip(), "%Y/%m/%d").date()
    except ValueError:
        raise UpstreamFormatError(f"{source} 日期格式已變更：{value!r}") from None


def number(value: str) -> Optional[Decimal]:
    """A price as published ("22935", "9.9", "5200.0000"); None for "-"."""
    return decimal_or_none(value)


def count(value: str) -> Optional[int]:
    """A volume / open interest ("62488"); None for "-"."""
    return int_or_none(value)
