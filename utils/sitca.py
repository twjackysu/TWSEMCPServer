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
from typing import Dict, List, Tuple

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


# --- 基金投資明細 (holdings) -------------------------------------------------------------
# www.sitca.org.tw/ROC/Industry/IN2629.aspx (monthly top 10) and IN2630.aspx (quarterly, every
# holding above 1% of NAV) are ASP.NET postback forms. Changing the period select posts the
# form back (__EVENTTARGET = ddlQ_YM) and the server rebuilds it for that period; querying any
# period but the default one without that step silently returns the first issuer's funds
# instead. So a query is GET → period postback → query, each POST carrying the previous
# reply's __VIEWSTATE / __EVENTVALIDATION and only the fields the page leaves enabled. No
# cookie is needed, so all three requests are cacheable. Querying by 類型代號 (the class SITCA
# files a fund under, e.g. AH11) returns every issuer's funds of that class. Rows carry fund
# names, not 證券代號.
SITCA_INDUSTRY_BASE = "https://www.sitca.org.tw/ROC/Industry"
HOLDINGS_MONTHLY_PAGE = "IN2629.aspx"
HOLDINGS_QUARTERLY_PAGE = "IN2630.aspx"
_FIELD_PREFIX = "ctl00$ContentPlaceHolder1$"
_HIDDEN_RE = re.compile(r'<input type="hidden" name="([^"]+)" id="[^"]*" value="([^"]*)"')
_HOLDINGS_YM_RE = re.compile(r'name="ctl00\$ContentPlaceHolder1\$ddlQ_YM"[^>]*>(.*?)</select>', re.S)
_ROW_RE = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S)
_CELL_RE = re.compile(r"<td([^>]*)>(.*?)</t[dh]>", re.S)
_TAG_RE = re.compile(r"<[^>]+>")
# Disclaimers follow the name after whitespace: "… ETF基金 (本基金之配息來源可能為…)". The ETF
# zone writes a multi-currency fund once per share class: "…指數基金-新台幣(配息)" (or, in
# older months, "…指數基金-新台幣").
_DISCLAIMER_RE = re.compile(r"\s+[（(].*$", re.S)
_SHARE_CLASS_RE = re.compile(r"-(?:新台幣|新臺幣|台幣|美元|人民幣|日圓|日幣|澳幣)(?:[（(][^)）]*[)）])?$")


def _holdings_page(client: TWSEAPIClient, page: str) -> str:
    return client.fetch_bytes(
        f"{SITCA_INDUSTRY_BASE}/{page}", headers=SITCA_HEADERS, timeout=60, cache_ttl=SITCA_CACHE_TTL
    ).decode("utf-8", errors="replace")


def holdings_months(client: TWSEAPIClient, page: str) -> List[str]:
    """YYYYMM periods a holdings page offers, newest first."""
    select = _HOLDINGS_YM_RE.search(_holdings_page(client, page))
    months = re.findall(r'<option[^>]*value="(\d{6})"', select.group(1)) if select else []
    if not months:
        raise ValueError(f"SITCA {page} 找不到資料月份選單，頁面可能改版")
    return sorted(set(months), reverse=True)


def fund_name_key(name: str) -> str:
    """Comparable fund name: disclaimer and share-class suffix removed, whitespace dropped."""
    name = _DISCLAIMER_RE.sub("", name.strip())
    return re.sub(r"\s", "", _SHARE_CLASS_RE.sub("", name))


def parse_holdings(html: str) -> Tuple[List[str], Dict[str, List[List[str]]]]:
    """(header, {fund name: holding rows}) from a holdings result page.

    The result table has no id, closes <td> with </th> in its header and spans the fund name
    over that fund's rows (rowspan), so rows one cell short belong to the fund above.
    """
    start = html.find("DTHeader")
    if start < 0:
        return [], {}
    table = html[html.rfind("<table", 0, start):]
    table = table[: table.find("</table>")]

    def clean(cell: str) -> str:
        return " ".join(_TAG_RE.sub(" ", cell.replace("<br>", " ")).replace("&nbsp;", " ").split())

    header: List[str] = []
    funds: Dict[str, List[List[str]]] = {}
    current = None
    for row in _ROW_RE.findall(table):
        cells = [clean(c) for _attrs, c in _CELL_RE.findall(row)]
        if not cells:
            continue
        if not header:
            header = cells
        elif len(cells) == len(header):
            current = cells[0]
            funds.setdefault(current, []).append(cells[1:])
        elif len(cells) == len(header) - 1 and current is not None:
            funds[current].append(cells)
    return header, funds


def _post_form(client: TWSEAPIClient, page: str, form: Dict[str, str]) -> str:
    return client.fetch_bytes(
        f"{SITCA_INDUSTRY_BASE}/{page}", data=form, method="POST", headers=SITCA_HEADERS, timeout=120,
        cache_ttl=SITCA_CACHE_TTL,
    ).decode("utf-8", errors="replace")


def holdings_by_class(client: TWSEAPIClient, page: str, ym: str, fund_class: str):
    """Every fund of one SITCA class for one period: (header, {fund name: rows})."""
    by_class = {_FIELD_PREFIX + "ddlQ_YM": ym, _FIELD_PREFIX + "rdo1": "rbClass"}
    period_page = _post_form(client, page, {
        **dict(_HIDDEN_RE.findall(_holdings_page(client, page))),
        "__EVENTTARGET": _FIELD_PREFIX + "ddlQ_YM", "__EVENTARGUMENT": "", **by_class,
    })
    html = _post_form(client, page, {
        **dict(_HIDDEN_RE.findall(period_page)), **by_class,
        _FIELD_PREFIX + "ddlQ_Class": fund_class, _FIELD_PREFIX + "BtnQuery": "查詢",
    })
    return parse_holdings(html)
