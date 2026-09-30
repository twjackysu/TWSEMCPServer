"""Shared helpers for TAIFEX (期交所) tools.

TAIFEX data comes from www.taifex.com.tw's HTML-form CSV download pages (``/cht/3/*Down``).
They accept any date range and, for the latest trading day, carry everything the
openapi.taifex.com.tw endpoints do (verified row by row on 2026-09-29; the download pages
also include rows and values openapi omits). A few tools still read openapi endpoints that
have no download-page counterpart.
"""

import csv
import io
from datetime import datetime, timedelta, timezone
from typing import Callable, List, Optional, Tuple

# TAIFEX requires a browser-like User-Agent (the default stock-mcp/1.0 gets HTML)
TAIFEX_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
}

TAIFEX_DOWNLOAD_BASE = "https://www.taifex.com.tw/cht/3"

# Download pages are re-queried when a tool first lists contracts and then fetches one of
# them, when the latest-day lookup re-walks the same empty days, and when several users ask
# about the same day. Five minutes keeps that to one request while still picking up the
# evening publication promptly.
TAIFEX_CACHE_TTL = 300

# How far back the "latest trading day" lookup walks. Covers the longest market closures
# (Lunar New Year) with room to spare.
LATEST_LOOKBACK_DAYS = 12

_TAIPEI = timezone(timedelta(hours=8))

ParsedCsv = Tuple[List[str], List[List[str]]]


def taipei_today() -> datetime:
    """Today's date in Taiwan (the server may run in another timezone)."""
    now = datetime.now(_TAIPEI)
    return datetime(now.year, now.month, now.day)


def parse_yyyymmdd(value: str) -> datetime:
    return datetime.strptime(value, "%Y%m%d")


def parse_date_range(
    start_date: str,
    end_date: str,
    max_span_days: int,
    example: str,
) -> Tuple[Optional[datetime], Optional[datetime], Optional[str]]:
    """Parse and validate the YYYYMMDD start/end pair every download tool takes.

    All of these tools reject a range on the same three grounds (unparseable date,
    reversed order, span over the client-side cap), so the checks live here instead of
    once per module. Returns (start_dt, end_dt, None) when the range is usable, or
    (None, None, message) carrying the Chinese message the tool should return verbatim.

    ``example`` is echoed in the format-error message so it matches the calling tool's
    own docstring example.
    """
    try:
        start_dt = parse_yyyymmdd(start_date)
        end_dt = parse_yyyymmdd(end_date)
    except ValueError:
        return None, None, (
            f"日期格式錯誤，請使用 YYYYMMDD 格式（例如 {example}），"
            f"收到：start_date={start_date}, end_date={end_date}"
        )

    if start_dt > end_dt:
        return None, None, f"起始日期 {start_date} 不可晚於結束日期 {end_date}"

    span_days = (end_dt - start_dt).days
    if span_days > max_span_days:
        return None, None, (
            f"查詢區間不可超過 {max_span_days} 天（收到 {span_days} 天），"
            f"請縮小 start_date～end_date 範圍後重試"
        )

    return start_dt, end_dt, None


def decode_and_parse_csv(body: bytes) -> Optional[ParsedCsv]:
    """Decode a Big5 (cp950) CSV response body from a www.taifex.com.tw download endpoint.

    These endpoints return an HTML alert page (not an HTTP error status) when the query is
    rejected (bad/out-of-range dates, missing contract), so that case is detected here and
    signaled as None rather than surfaced as parsed rows. Returns (header, data_rows).
    """
    # cp950 (Microsoft's Big5) rather than Python's strict big5: TAIFEX's CSVs use its
    # extension characters, e.g. 碁 in 宏碁期貨, which big5 turns into mojibake.
    text = body.decode("cp950", errors="replace")
    # Rejected queries and days with nothing published yet come back as an HTML page
    # (starting with <!DOCTYPE HTML ...> or <html>), never as CSV.
    if "DateTime error" in text or text.lstrip().startswith("<"):
        return None

    rows = list(csv.reader(io.StringIO(text)))
    if len(rows) < 2:
        return None

    header, data_rows = rows[0], rows[1:]
    # Tolerate a 1-column length mismatch: some endpoints (e.g. optDataDown) have a
    # trailing comma in the header row that isn't present in data rows.
    min_cols = max(len(header) - 1, 1)
    # Blank lines parse as [] — a day with nothing published yet comes back as a header
    # followed by blank lines.
    data_rows = [r for r in data_rows if len(r) >= min_cols and r[0].strip()]
    if not data_rows:
        return None
    return header, data_rows


def fetch_period(
    fetch: Callable[[datetime, datetime], Optional[ParsedCsv]],
    start_date: str,
    end_date: str,
    max_span_days: int,
    example: str,
    is_complete: Optional[Callable[[ParsedCsv], bool]] = None,
) -> Tuple[Optional[ParsedCsv], str, Optional[str]]:
    """Run ``fetch`` for the requested period, or for the latest trading day when both
    dates are empty.

    Returns (parsed or None, human label of the period, error message or None). With no
    dates it walks back from today (Taiwan time) one day per request until a day has data,
    so a weekend or holiday costs a few small requests rather than one large multi-day
    download. ``is_complete`` lets a caller skip a day that only has part of its data so
    far (e.g. only the overnight 盤後 session while the regular session is still trading).
    """
    if not start_date and not end_date:
        day = taipei_today()
        for _ in range(LATEST_LOOKBACK_DAYS):
            parsed = fetch(day, day)
            if parsed is not None and (is_complete is None or is_complete(parsed)):
                return parsed, f"{day:%Y%m%d}（最新交易日）", None
            day -= timedelta(days=1)
        return None, "最新交易日", None

    start_date, end_date = start_date or end_date, end_date or start_date
    start_dt, end_dt, error = parse_date_range(start_date, end_date, max_span_days, example)
    if error:
        return None, "", error
    label = start_date if start_date == end_date else f"{start_date}～{end_date}"
    return fetch(start_dt, end_dt), label, None


def download_form(start_dt: datetime, end_dt: datetime, **extra: str) -> dict:
    """The form fields every download page takes, plus endpoint-specific ones."""
    return {"queryStartDate": f"{start_dt:%Y/%m/%d}", "queryEndDate": f"{end_dt:%Y/%m/%d}", **extra}


def is_contract_code(value: str) -> bool:
    """True for a contract code such as TX / TXF / TXO, False for a Chinese name like 臺股期貨."""
    return value.isascii() and value.replace("_", "").isalnum()
