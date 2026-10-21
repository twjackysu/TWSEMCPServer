"""Company listing related tools.

Which field holds the listing date depends on the endpoint (TWSE's swagger descriptions, checked
2026-10-21 against each stock's first STOCK_DAY trading day):

- /company/newlisting, /company/applylistingLocal: ``ApprovedListingDate`` is 股票上市買賣日期 (the
  listing date). Despite its name, ``ListingDate`` there is 證期局核准上市契約日期, the regulator's
  approval of the listing contract, and is blank for nearly every row since 2016.
- /company/applylistingForeign: ``ListingDate`` is 股票上市買賣日期; there is no ApprovedListingDate.
"""

from typing import Optional
from fastmcp import FastMCP
from utils import TWSEAPIClient, create_list_tool
from utils.date_helper import roc_to_ad
from utils.types import TWSEDataItem


def _doc(summary: str) -> str:
    return "\n".join([
        summary, "",
        "        Args:",
        "            name: 公司名稱關鍵字（選填）",
        "            limit: 回傳筆數上限（預設 50）",
        "            offset: 跳過前 N 筆（預設 0，搭配 limit 分頁）",
    ])


def _date(value) -> str:
    """A TWSE ROC date ("1151020", "0890310") as "2026-10-20"; "—" when blank."""
    text = str(value or "").strip()
    if text.isdigit() and len(text) == 7:
        return roc_to_ad(text)
    return text or "—"


def _application_formatter(listing_date_field: str):
    def formatter(i):
        return (
            f"- {i.get('Company', 'N/A')} ({i.get('Code', 'N/A')}): "
            f"申請日期 {_date(i.get('ApplicationDate'))}, 董事會通過上市 {_date(i.get('ApprovedDate'))}, "
            f"上市日期 {_date(i.get(listing_date_field))}\n"
        )
    return formatter


# The keys /company/applylistingLocal puts its first nine columns under, and the columns they
# really hold. Its rows carry a leading 序號 column and lack the 證期局核准上市契約日期 column, so
# each of these keys holds the next column's value; from ApprovedListingDate on the keys line up.
# Found 2026-10-21 by comparing companies present in both this feed and /company/newlisting.
_LOCAL_SERVED_KEYS = ("Code", "Company", "ApplicationDate", "Chairman", "AmountofCapital ",
                      "CommitteeDate", "ApprovedDate", "AgreementDate", "ListingDate")
_LOCAL_ACTUAL_KEYS = ("No", "Code", "Company", "ApplicationDate", "Chairman", "AmountofCapital ",
                      "CommitteeDate", "ApprovedDate", "AgreementDate")


def normalize_local_application(row: TWSEDataItem) -> TWSEDataItem:
    """Put a shifted /company/applylistingLocal row back under its real keys.

    Decided per row — a company name, not a date, under ApplicationDate — so rows already served
    under the right keys (if TWSE fixes the feed) pass through unchanged.
    """
    if all(ch.isdigit() for ch in str(row.get("ApplicationDate", ""))):
        return row
    fixed = dict(row)
    for served, actual in zip(_LOCAL_SERVED_KEYS, _LOCAL_ACTUAL_KEYS):
        fixed[actual] = row.get(served, "")
    fixed["ListingDate"] = ""  # 證期局核准上市契約日期: not in this layout
    return fixed


# (endpoint, name, summary, label, empty_data_type, formatter, normalize)
LISTING_TOOLS = [
    (
        "/company/applylistingForeign", "get_foreign_companies_applying_for_listing",
        "查詢外國公司向證交所申請第一上市之公司。", "外國公司申請第一上市資料",
        "外國公司申請第一上市", _application_formatter("ListingDate"), None,
    ),
    (
        "/company/newlisting", "get_recently_listed_companies",
        "查詢最近上市公司，由新到舊（上市日期＝股票上市買賣日）。", "最近上市公司資料", "最近上市公司",
        lambda i: f"- {i.get('Company', 'N/A')} ({i.get('Code', 'N/A')}): 上市日期 {_date(i.get('ApprovedListingDate'))}\n",
        None,
    ),
    (
        "/company/suspendListingCsvAndHtml", "get_suspended_listed_companies",
        "查詢終止上市公司。", "終止上市公司資料", "終止上市公司",
        lambda i: f"- {i.get('Company', 'N/A')} ({i.get('Code', 'N/A')}): 終止日期 {i.get('DelistingDate', 'N/A')}\n",
        None,
    ),
    (
        "/company/applylistingLocal", "get_local_companies_applying_for_listing",
        "查詢申請上市之本國公司（上市日期＝股票上市買賣日，尚未排定時為 —）。", "申請上市之本國公司資料",
        "申請上市之本國公司", _application_formatter("ApprovedListingDate"), normalize_local_application,
    ),
]


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    """Register company listing tools with the MCP instance."""

    for endpoint, name, summary, label, empty_type, formatter, normalize in LISTING_TOOLS:
        create_list_tool(
            mcp, endpoint, name, _doc(summary), label, empty_type,
            formatter, filter_field="Company", client=client, normalize=normalize,
        )
