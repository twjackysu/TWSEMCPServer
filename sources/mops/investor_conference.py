"""MOPS ajax_t100sb02_1: 法人說明會 — investor conferences of one market in a year or a month, or of one company.

Legacy page: ``POST mopsov.twse.com.tw/mops/web/ajax_t100sb02_1`` with ``TYPEK`` (sii / otc / rotc / pub), ``year``
(ROC), ``month`` (zero-padded "09"; "9" answers 查無資料; "" = the whole year) and ``co_id`` ("" = every company).
The reply is HTML with ``table#myTable`` under a two-row header::

    公司代號 | 公司名稱 | 召開法人說明會日期 | 召開法人說明會時間 | 召開法人說明會地點 | 法人說明會擇要訊息 | 法人說明會簡報內容 | …
                                                                                                        中文檔案 | 英文檔案
    1477 | 聚陽 | 115/01/08 | 14:00 | 線上法說會 | 介紹本公司之營運概況… | 147720251110M002.pdf | 147720251110E002.pdf | …

then 公司網站是否提供法人說明會相關資訊, 影音連結資訊, 其他應敘明事項 and a 歷年法人說明會 button. 興櫃 (rotc) and
公開發行 (pub) pages name the website column 公司網站是否提供法人說明會內容 and have no 影音連結資訊. Rows come ordered by
company code. A query without rows is a page saying 查無資料. Same headers checked 2010–2026.
"""

from dataclasses import dataclass
from typing import List, Optional

from utils.api_client import TWSEAPIClient
from utils.errors import UpstreamFormatError
from utils.mops import mops_legacy_post, parse_html_table

from ..columns import column_index
from .legacy import UNEXPECTED_PAGE, two_row_header

SOURCE = "t100sb02_1"
NO_DATA_TEXT = "查無資料"
GROUPS = {"法人說明會簡報內容": ("中文檔案", "英文檔案")}
FIELDS = ("公司代號", "公司名稱", "召開法人說明會日期", "召開法人說明會時間", "召開法人說明會地點", "法人說明會擇要訊息",
          "法人說明會簡報內容/中文檔案", "法人說明會簡報內容/英文檔案", "其他應敘明事項")
WEBSITE = ("公司網站是否提供法人說明會相關資訊", "公司網站是否提供法人說明會內容")  # sii / otc; rotc / pub
VIDEO = "影音連結資訊"  # sii / otc only


@dataclass(frozen=True)
class Conference:
    code: str
    name: str
    date: str          # 召開法人說明會日期, ROC as published ("115/01/08")
    time: str          # 召開法人說明會時間 ("14:00")
    place: str         # 召開法人說明會地點
    summary: str       # 法人說明會擇要訊息
    file_zh: str       # 簡報中文檔案 name ("147720251110M002.pdf"); "" when none
    file_en: str       # 簡報英文檔案
    website: str       # 公司網站是否提供法人說明會相關資訊 (usually the URL)
    video: str         # 影音連結資訊; "" on rotc / pub pages, which have no such column
    other: str         # 其他應敘明事項


def investor_conferences(client: TWSEAPIClient, market: str, roc_year: int, month: Optional[int] = None,
                         code: str = "") -> List[Conference]:
    """Conferences in ``market`` in ROC year ``roc_year`` (and ``month``), of ``code`` or every company, in MOPS's
    order; empty when MOPS has none. Raises ``UpstreamFormatError`` on a page without the table (MOPS restricting
    access, or a redesign) or a changed header."""
    html = mops_legacy_post(client, "ajax_t100sb02_1", {
        "TYPEK": market, "year": str(roc_year), "month": f"{month:02d}" if month else "", "co_id": code,
    })
    rows = parse_html_table(html, "myTable")
    if len(rows) < 2:
        if NO_DATA_TEXT in html:
            return []
        raise UpstreamFormatError(UNEXPECTED_PAGE)
    names = two_row_header(rows[0], rows[1], GROUPS, SOURCE)
    website = next((n for n in WEBSITE if n in names), WEBSITE[0])  # neither: column_index reports the first missing
    col = column_index(names, FIELDS + (website,), SOURCE)
    video = names.index(VIDEO) if VIDEO in names else None
    conferences = []
    for r in rows[2:]:
        if len(r) != len(names):
            raise UpstreamFormatError(f"{SOURCE} 資料列有 {len(r)} 格，表頭有 {len(names)} 欄：{r}")
        conferences.append(Conference(
            code=r[col["公司代號"]], name=r[col["公司名稱"]], date=r[col["召開法人說明會日期"]],
            time=r[col["召開法人說明會時間"]], place=r[col["召開法人說明會地點"]], summary=r[col["法人說明會擇要訊息"]],
            file_zh=r[col["法人說明會簡報內容/中文檔案"]], file_en=r[col["法人說明會簡報內容/英文檔案"]],
            website=r[col[website]], video=r[video] if video is not None else "", other=r[col["其他應敘明事項"]],
        ))
    return conferences
