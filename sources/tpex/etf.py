"""TPEx website ETF/list and ETF/detail: the TPEx-listed ETFs of one type, and one ETF's specification.

``POST https://www.tpex.org.tw/www/zh-tw/ETF/list`` with ``type`` (domestic / foreign / bond) and ``response=json``::

    {"stat": "ok", "date": "20261022",
     "tables": [{"title": "國內成分股ETF", "fields": ["證券代號", "ETF簡稱", "上櫃日期"],
                 "data": [["006201", "元大富櫃50", "100/01/27"], ["00928", "中信上櫃ESG30", "112/05/24"], …]}]}

``POST …/ETF/detail`` with ``type``, ``code`` and ``response=json``: three tables of one row each — 商品規格 (名稱, ETF簡稱,
證券代號, ETF類別, 上櫃日期, 基金經理公司, 標的指數, …, 管理費, 保管費, …, 基金經理公司網站), 申購買回清單PCF (one unnamed
field holding a link to the issuer's site) and 標的指數資訊. Cells may hold HTML links
(``<a href="http://www.yuantaetfs.com/" target="_blank">http://www.yuantaetfs.com/</a>``); the gateway keeps their text.
"""

import json
import re
from dataclasses import dataclass
from typing import List, Literal, Tuple

from utils.api_client import TWSEAPIClient
from utils.errors import UpstreamFormatError

from ..columns import column_index

ETF_LIST_URL = "https://www.tpex.org.tw/www/zh-tw/ETF/list"
ETF_DETAIL_URL = "https://www.tpex.org.tw/www/zh-tw/ETF/detail"
EtfType = Literal["domestic", "foreign", "bond"]
ETF_TYPES: Tuple[EtfType, ...] = ("domestic", "foreign", "bond")
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
# ETFs are listed a few times a month and their specifications rarely change.
CACHE_TTL = 6 * 3600
_TAG_RE = re.compile(r"<[^>]+>")


@dataclass(frozen=True)
class TpexEtf:
    code: str    # 證券代號
    name: str    # ETF簡稱
    listed: str  # 上櫃日期, ROC as published ("100/01/27")


@dataclass(frozen=True)
class DetailSection:
    title: str                        # 商品規格, 標的指數資訊
    items: Tuple[Tuple[str, str], ...]  # (field, value) in published order, HTML tags removed, whitespace collapsed


def _post(client: TWSEAPIClient, url: str, form: dict) -> dict:
    body = client.fetch_bytes(url, data={**form, "response": "json"}, method="POST", headers=HEADERS, timeout=60,
                              cache_ttl=CACHE_TTL)
    try:
        resp = json.loads(body.decode("utf-8"))
    except ValueError:
        raise UpstreamFormatError(f"櫃買中心 {url.rsplit('/', 1)[-1]} 回應不是 JSON：{body[:80]!r}") from None
    if not isinstance(resp, dict) or not isinstance(resp.get("tables"), list):
        raise UpstreamFormatError(f"櫃買中心 {url.rsplit('/', 1)[-1]} 回應結構已變更：{str(resp)[:200]}")
    return resp


def _text(cell) -> str:
    return " ".join(_TAG_RE.sub(" ", str(cell)).split())


def tpex_etfs(client: TWSEAPIClient, etf_type: EtfType) -> List[TpexEtf]:
    """The TPEx-listed ETFs of ``etf_type``, in TPEx's order."""
    tables = _post(client, ETF_LIST_URL, {"type": etf_type})["tables"]
    if not tables:
        return []
    table = tables[0]
    col = column_index(table.get("fields"), ("證券代號", "ETF簡稱", "上櫃日期"), "ETF/list")
    return [TpexEtf(code=str(r[col["證券代號"]]).strip(), name=str(r[col["ETF簡稱"]]).strip(),
                    listed=str(r[col["上櫃日期"]]).strip())
            for r in table.get("data") or [] if r]


def tpex_etf_detail(client: TWSEAPIClient, etf_type: EtfType, code: str) -> List[DetailSection]:
    """``code``'s specification tables in TPEx's order; the PCF table (only an unnamed link) and tables without a row
    are left out. Raises ``UpstreamFormatError`` if a table has more than one row or a row does not match its fields."""
    sections = []
    for table in _post(client, ETF_DETAIL_URL, {"type": etf_type, "code": code})["tables"]:
        fields, data = [str(f).strip() for f in table.get("fields") or []], table.get("data") or []
        if not data or not any(fields):
            continue
        if len(data) > 1 or len(data[0]) != len(fields):
            raise UpstreamFormatError(f"ETF/detail {table.get('title')} 不再是一列對應 {len(fields)} 個欄位：{str(data)[:200]}")
        sections.append(DetailSection(title=str(table.get("title") or ""),
                                      items=tuple(zip(fields, map(_text, data[0]), strict=True))))
    return sections
