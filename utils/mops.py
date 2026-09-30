"""Shared helpers for 公開資訊觀測站 (MOPS) endpoints.

MOPS has no public API docs. Its 2024+ SPA front end (mops.twse.com.tw) calls two kinds of
backend, and each page's form field names live in that page's JS chunk
(``https://mops.twse.com.tw/mops/assets/<pageId>.js``, action ``{apiName, type}``):

- ``type: "base"`` → ``POST /mops/api/<apiName>`` with a JSON body. Replies
  ``{"code": 200, "message": "查詢成功", "result": {...}}``; on failure ``code`` is
  500 (bad parameters, e.g. unknown company) or 406 (查無相符資料) and ``result`` is null.
- ``type: "twse"`` → the legacy site: ``POST mopsov.twse.com.tw/mops/web/<apiName>``,
  form-encoded, returning an HTML fragment.

Result tables come as ``titles`` (a tree of ``{"main", "sub"}`` headers, with grouped
columns nested under ``sub``) plus ``data`` / ``reportList`` rows whose width equals the
number of leaf headers.
"""

from html.parser import HTMLParser
from typing import Any, Dict, List, Optional

from .api_client import TWSEAPIClient

MOPS_API_BASE = "https://mops.twse.com.tw/mops/api"
MOPS_LEGACY_BASE = "https://mopsov.twse.com.tw/mops/web"

# MOPS data changes at most when a company files; past periods never do. Caching for a
# few minutes lets a prompt that calls several statement/revenue tools for the same company
# (or a multi-month revenue range repeated by another user) skip MOPS entirely, which also
# keeps us clear of MOPS's anti-crawling throttle.
MOPS_CACHE_TTL = 600

# Every legacy ajax_* page is submitted with these hidden form fields (the SPA's
# ``hideTheKey``); without them the old site answers with an empty shell page.
MOPS_LEGACY_HIDDEN_FIELDS = {"encodeURIComponent": "1", "step": "1", "firstin": "1", "off": "1"}


class MopsQueryError(Exception):
    """MOPS answered, but with a non-200 ``code`` (bad parameters or no matching data)."""

    def __init__(self, code: Any, message: str):
        super().__init__(f"MOPS 回應 code={code}: {message}")
        self.code = code
        self.message = message


def to_roc_year(year: str) -> int:
    """Accept a western (2025) or ROC (114) year string and return the ROC year."""
    value = int(str(year).strip())
    return value - 1911 if value > 1911 else value


def mops_post(client: TWSEAPIClient, api_name: str, body: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """POST ``body`` to ``/mops/api/<api_name>`` and return ``result``.

    Returns None when MOPS says there is simply no data (code 406). Any other non-200
    code raises ``MopsQueryError`` so the tool reports the upstream message instead of a
    misleading "no data".
    """
    resp = client.fetch_json(f"{MOPS_API_BASE}/{api_name}", json_body=body, cache_ttl=MOPS_CACHE_TTL)
    if not isinstance(resp, dict):
        raise ValueError(f"MOPS {api_name} 回應格式非預期: {type(resp).__name__}")
    code = str(resp.get("code"))
    if code == "200":
        return resp.get("result")
    if code == "406":
        return None
    raise MopsQueryError(resp.get("code"), str(resp.get("message", "")))


def mops_legacy_post(client: TWSEAPIClient, api_name: str, form: Dict[str, Any]) -> str:
    """POST a form to the legacy ``mopsov`` site and return the decoded HTML."""
    body = client.fetch_bytes(
        f"{MOPS_LEGACY_BASE}/{api_name}",
        method="POST",
        data={**MOPS_LEGACY_HIDDEN_FIELDS, **form},
        cache_ttl=MOPS_CACHE_TTL,
    )
    return body.decode("utf-8", errors="replace")


def flatten_titles(titles: List[Dict[str, Any]], prefix: str = "") -> List[str]:
    """Flatten MOPS's nested header tree into one label per data column.

    ``[{"main": "114年第2季", "sub": [{"main": "金額"}, {"main": "%"}]}]`` becomes
    ``["114年第2季 金額", "114年第2季 %"]`` — the same order as the row cells.
    """
    labels: List[str] = []
    for node in titles or []:
        name = str(node.get("main", "")).strip()
        full = f"{prefix} {name}".strip() if prefix else name
        subs = node.get("sub") or []
        if subs:
            labels.extend(flatten_titles(subs, full))
        else:
            labels.append(full)
    return labels


def leaf_titles(titles: List[Dict[str, Any]]) -> List[str]:
    """Leaf header names without their group prefix (for looking columns up by name)."""
    labels: List[str] = []
    for node in titles or []:
        subs = node.get("sub") or []
        if subs:
            labels.extend(leaf_titles(subs))
        else:
            labels.append(str(node.get("main", "")).strip())
    return labels


class _TableParser(HTMLParser):
    """Collect every ``<tr>`` of the first ``<table>`` whose id matches, as text cells."""

    def __init__(self, table_id: str):
        super().__init__(convert_charrefs=True)
        self.table_id = table_id
        self.depth = 0  # nesting depth inside the target table; 0 = outside
        self.rows: List[List[str]] = []
        self._row: Optional[List[str]] = None
        self._cell: Optional[List[str]] = None
        self._done = False

    def handle_starttag(self, tag, attrs):
        if self._done:
            return
        if tag == "table":
            if self.depth:
                self.depth += 1
            elif dict(attrs).get("id") == self.table_id:
                self.depth = 1
            return
        if tag == "br" and self._cell is not None:
            self._cell.append(" ")
        # Rows/cells of a table nested inside a cell are folded into that cell's text.
        if self.depth != 1:
            return
        if tag == "tr":
            self._row = []
        elif tag in ("td", "th") and self._row is not None:
            self._cell = []

    def handle_endtag(self, tag):
        if not self.depth or self._done:
            return
        if tag == "table":
            self.depth -= 1
            if not self.depth:
                self._done = True
        elif self.depth != 1:
            return
        elif tag in ("td", "th") and self._cell is not None and self._row is not None:
            self._row.append(" ".join("".join(self._cell).split()))
            self._cell = None
        elif tag == "tr" and self._row is not None:
            self.rows.append(self._row)
            self._row = None

    def handle_data(self, data):
        if self.depth and self._cell is not None:
            self._cell.append(data)


def parse_html_table(html: str, table_id: str) -> List[List[str]]:
    """Return the rows (header rows included) of ``<table id=table_id>`` as text cells."""
    parser = _TableParser(table_id)
    parser.feed(html)
    return parser.rows
