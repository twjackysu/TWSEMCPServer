"""Company listing related tools.

Which field holds the listing date depends on the endpoint (TWSE's swagger descriptions, checked
2026-10-21 against each stock's first STOCK_DAY trading day):

- /company/newlisting, /company/applylistingLocal: ``ApprovedListingDate`` is 股票上市買賣日期 (the
  listing date). Despite its name, ``ListingDate`` there is 證期局核准上市契約日期, the regulator's
  approval of the listing contract, and is blank for nearly every row since 2016.
- /company/applylistingForeign: ``ListingDate`` is 股票上市買賣日期; there is no ApprovedListingDate.
"""

from typing import List, Optional
from fastmcp import FastMCP
from utils import TWSEAPIClient
from utils.date_helper import roc_to_ad
from utils.types import TWSEDataItem
from toolkit import ListToolSpec, create_list_tool


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
    for served, actual in zip(_LOCAL_SERVED_KEYS, _LOCAL_ACTUAL_KEYS, strict=True):
        fixed[actual] = row.get(served, "")
    fixed["ListingDate"] = ""  # 證期局核准上市契約日期: not in this layout
    return fixed


_COMPANY_NAME_HINT = "公司名稱關鍵字（選填）"

LISTING_TOOLS: List[ListToolSpec] = [
    ListToolSpec(
        endpoint="/company/applylistingForeign", name="get_foreign_companies_applying_for_listing",
        summary="查詢外國公司向證交所申請第一上市之公司。",
        label="外國公司申請第一上市資料", empty_data_type="外國公司申請第一上市",
        filter_field="Company", name_hint=_COMPANY_NAME_HINT,
        formatter=_application_formatter("ListingDate"),
    ),
    ListToolSpec(
        endpoint="/company/newlisting", name="get_recently_listed_companies",
        summary="查詢最近上市公司，由新到舊（上市日期＝股票上市買賣日）。",
        label="最近上市公司資料", empty_data_type="最近上市公司",
        filter_field="Company", name_hint=_COMPANY_NAME_HINT,
        formatter=lambda i: f"- {i.get('Company', 'N/A')} ({i.get('Code', 'N/A')}): 上市日期 {_date(i.get('ApprovedListingDate'))}\n",
    ),
    ListToolSpec(
        endpoint="/company/suspendListingCsvAndHtml", name="get_suspended_listed_companies",
        summary="查詢終止上市公司。",
        label="終止上市公司資料", empty_data_type="終止上市公司",
        filter_field="Company", name_hint=_COMPANY_NAME_HINT,
        formatter=lambda i: f"- {i.get('Company', 'N/A')} ({i.get('Code', 'N/A')}): 終止日期 {i.get('DelistingDate', 'N/A')}\n",
    ),
    ListToolSpec(
        endpoint="/company/applylistingLocal", name="get_local_companies_applying_for_listing",
        summary="查詢申請上市之本國公司（上市日期＝股票上市買賣日，尚未排定時為 —）。",
        label="申請上市之本國公司資料", empty_data_type="申請上市之本國公司",
        filter_field="Company", name_hint=_COMPANY_NAME_HINT,
        formatter=_application_formatter("ApprovedListingDate"),
        normalize=normalize_local_application,
    ),
]


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    """Register company listing tools with the MCP instance."""

    for spec in LISTING_TOOLS:
        create_list_tool(mcp, spec, client)
