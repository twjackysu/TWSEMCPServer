"""MOPS 重大訊息: t05st01 (one company's announcements in a year), t05st02 (every announcement on one day) and the
full text behind each (t05st01_detail / t05st02_detail).

``POST https://mops.twse.com.tw/mops/api/t05st01`` with ``{"companyId", "year" (ROC), "month": "all", "firstDay": "",
"lastDay": ""}``; ``t05st02`` with ``{"year" (ROC), "month", "day"}``. Both reply ``{"titles", "data"}`` (t05st01 adds
``companyAbbreviation``)::

    t05st01  公司代號, 公司名稱, 發言日期, 發言時間, 主旨, 詳細資料
    t05st02  發言日期, 發言時間, 公司代號, 公司名稱, 主旨, 詳細資料
             ["115/10/21", "17:32:37", "3712", "永崴投控", "公告本公司…", {"apiName": "t05st02_detail",
              "parameters": {"companyId": "3712", "marketKind": "sii", "enterDate": "1151021", "serialNumber": "1"}}]

詳細資料 is the link to the full text: POST its ``parameters`` to its ``apiName``; that reply's one row has 序號, 發言日期,
發言時間, 發言人, 發言人職稱, 發言人電話, 主旨, 符合條款, 事實發生日, 說明 (發言人, 職稱 and 主旨 padded with spaces).
Dates are ROC as published ("115/09/10"); 主旨 keeps its line breaks. Columns are found by title; same titles checked
2010–2026.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence

from utils.api_client import TWSEAPIClient
from utils.date_helper import roc_year_of
from utils.errors import UpstreamFormatError
from utils.mops import leaf_titles, mops_post

from ..columns import column_index

LIST_FIELDS = ("公司代號", "公司名稱", "發言日期", "發言時間", "主旨", "詳細資料")
DETAIL_FIELDS = ("發言日期", "發言時間", "發言人", "發言人職稱", "主旨", "符合條款", "事實發生日", "說明")


@dataclass(frozen=True)
class NewsLink:
    """詳細資料: where the full text is."""
    api_name: str                # t05st01_detail / t05st02_detail
    parameters: Dict[str, Any]   # companyId, marketKind (sii / otc / rotc / pub), enterDate, serialNumber


@dataclass(frozen=True)
class Announcement:
    code: str
    name: str
    date: str                    # 發言日期 as published, ROC ("115/09/10")
    time: str                    # 發言時間 ("14:16:41")
    subject: str                 # 主旨, line breaks kept
    link: Optional[NewsLink]     # None when the row has no usable 詳細資料

    @property
    def market(self) -> str:
        """sii / otc / rotc / pub, from the link; "" without one."""
        return str(self.link.parameters.get("marketKind", "")) if self.link else ""


@dataclass(frozen=True)
class CompanyNews:
    name: str                    # companyAbbreviation; "" when MOPS leaves it out
    announcements: List[Announcement]  # in MOPS's order


@dataclass(frozen=True)
class AnnouncementDetail:
    date: str
    time: str
    spokesperson: str            # 發言人
    spokesperson_title: str      # 發言人職稱
    subject: str
    clause: str                  # 符合條款 ("第20款")
    fact_date: str               # 事實發生日, ROC as published
    text: str                    # 說明, line breaks kept


def _columns(result: Dict[str, Any], fields: Sequence[str], source: str):
    names = leaf_titles(result.get("titles") or [])
    col = column_index(names, fields, source)
    rows = result.get("data") or []
    for r in rows:
        if not isinstance(r, list) or len(r) != len(names):
            raise UpstreamFormatError(f"{source} 資料列與 titles 對不上（{len(names)} 欄）：{str(r)[:200]}")
    return col, rows


def _link(cell) -> Optional[NewsLink]:
    if not isinstance(cell, dict) or not cell.get("apiName"):
        return None
    return NewsLink(api_name=str(cell["apiName"]), parameters=dict(cell.get("parameters") or {}))


def _announcements(result: Dict[str, Any], source: str) -> List[Announcement]:
    if not result.get("data"):
        return []
    col, rows = _columns(result, LIST_FIELDS, source)
    return [Announcement(
        code=str(r[col["公司代號"]]).strip(),
        name=str(r[col["公司名稱"]]).strip(),
        date=str(r[col["發言日期"]]).strip(),
        time=str(r[col["發言時間"]]).strip(),
        subject=str(r[col["主旨"]]),
        link=_link(r[col["詳細資料"]]),
    ) for r in rows]


def company_news(client: TWSEAPIClient, code: str, roc_year: int) -> Optional[CompanyNews]:
    """``code``'s announcements in ROC year ``roc_year``, or None when MOPS has none. Raises
    ``UpstreamFormatError`` if the titles changed."""
    result = mops_post(client, "t05st01", {"companyId": code, "year": str(roc_year), "month": "all",
                                           "firstDay": "", "lastDay": ""})
    if not result:
        return None
    return CompanyNews(name=str(result.get("companyAbbreviation") or "").strip(),
                       announcements=_announcements(result, "t05st01"))


def market_news(client: TWSEAPIClient, date: str) -> List[Announcement]:
    """Every announcement MOPS lists for ``date`` (YYYYMMDD); empty when there are none. Raises
    ``UpstreamFormatError`` if the titles changed."""
    result = mops_post(client, "t05st02", {"year": str(roc_year_of(date)), "month": date[4:6], "day": date[6:]})
    return _announcements(result, "t05st02") if result else []


def news_detail(client: TWSEAPIClient, link: NewsLink) -> Optional[AnnouncementDetail]:
    """The full text behind ``link``, or None when MOPS has none. Raises ``UpstreamFormatError`` if the titles
    changed."""
    result = mops_post(client, link.api_name, link.parameters)
    if not result or not result.get("data"):
        return None
    col, rows = _columns(result, DETAIL_FIELDS, link.api_name)
    r = rows[0]
    return AnnouncementDetail(
        date=str(r[col["發言日期"]]).strip(),
        time=str(r[col["發言時間"]]).strip(),
        spokesperson=str(r[col["發言人"]]).strip(),
        spokesperson_title=str(r[col["發言人職稱"]]).strip(),
        subject=str(r[col["主旨"]]).strip(),
        clause=str(r[col["符合條款"]]).strip(),
        fact_date=str(r[col["事實發生日"]]).strip(),
        text=str(r[col["說明"]]).strip(),
    )
