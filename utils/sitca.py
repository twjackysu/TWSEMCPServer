"""Helpers for the 投信投顧公會 (SITCA) ETF zone, www.sitca.org.tw/ROC/SITCA_ETF/.

Every domestic ETF of every SITCA member (both TWSE- and TPEx-listed, ~340 funds) is on
these pages, keyed by 證券代號. Each query page (``etf_info.aspx``, ``etf_statement.aspx``)
is a form whose 查詢 button only builds a GET URL for the result page in an iframe
(``etf_info2.aspx``, ``etf_statement2.aspx``), so the result pages are read directly:

    <page>2.aspx?txtYM=YYYYMM&txtcomid=&txtfund=&txtemcode=<code>,&txtkeyword=&txtR1=1&txtR2=1

``txtemcode`` empty returns every ETF. ``txtYM`` must be one of the months in the query
page's ``ddlYM`` select (the info page only offers the latest month). Months before about
2024 carry no 證券代號 ("-" in every row), so a code finds nothing there; those months are
queried by 基金統編 instead (``txtfund=<統編>,``), which every month has. Futures-trust ETFs
(期信, e.g. 00635U) and foreign-currency share codes (e.g. 00625K) are not SITCA funds, so
they are absent; a fund appears from its first monthly report.
"""

import re
from typing import List, Optional

from .api_client import TWSEAPIClient
from .mops import parse_html_table

SITCA_ETF_BASE = "https://www.sitca.org.tw/ROC/SITCA_ETF"
# Monthly data, published around the 10th business day of the next month.
SITCA_CACHE_TTL = 6 * 3600
SITCA_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

# The result grid sits inside a layout table, so it is read by its id.
GRID_ID = "ctl00_ContentPlaceHolder1_GridView1"
_YM_SELECT_RE = re.compile(r'name="ctl00\$ContentPlaceHolder1\$ddlYM"[^>]*>(.*?)</select>', re.S)


def available_months(client: TWSEAPIClient, page: str) -> List[str]:
    """YYYYMM months a SITCA ETF query page offers, newest first."""
    html = client.fetch_bytes(
        f"{SITCA_ETF_BASE}/{page}", headers=SITCA_HEADERS, timeout=60, cache_ttl=SITCA_CACHE_TTL
    ).decode("utf-8", errors="replace")
    select = _YM_SELECT_RE.search(html)
    months = re.findall(r'<option[^>]*value="(\d{6})"', select.group(1)) if select else []
    if not months:
        raise ValueError(f"SITCA {page} 找不到資料月份選單，頁面可能改版")
    return months


def query_rows(client: TWSEAPIClient, result_page: str, ym: str, code: str = "",
               fund_id: str = "") -> List[List[str]]:
    """Header row + data rows of a SITCA ETF result page (the 合計 row dropped).

    Filter by ``code`` (證券代號) or ``fund_id`` (基金統編); neither returns every ETF.
    Rows of funds without a 證券代號 that month keep "-".
    """
    params = {"txtYM": ym, "txtcomid": "", "txtfund": f"{fund_id}," if fund_id else "",
              "txtemcode": f"{code}," if code else "", "txtkeyword": "", "txtR1": "1", "txtR2": "1"}
    html = client.fetch_bytes(
        f"{SITCA_ETF_BASE}/{result_page}", params=params, headers=SITCA_HEADERS, timeout=120,
        cache_ttl=SITCA_CACHE_TTL,
    ).decode("utf-8", errors="replace")
    table = parse_html_table(html, GRID_ID)
    if not table or not table[0] or table[0][0] != "序號":
        return []
    return [table[0]] + [r for r in table[1:] if r and r[0].isdigit()]


def to_number(text: str) -> Optional[float]:
    """"2,384,122,964,603" / "14.5%" / "106.6400" → float; "-" or blank → None."""
    text = (text or "").replace(",", "").replace("%", "").strip()
    try:
        return float(text)
    except ValueError:
        return None
