"""Company listing related tools."""

from typing import Optional
from fastmcp import FastMCP
from utils import TWSEAPIClient, create_list_tool


def _doc(summary: str) -> str:
    return "\n".join([
        summary, "",
        "        Args:",
        "            name: 公司名稱關鍵字（選填）",
        "            limit: 回傳筆數上限（預設 50）",
        "            offset: 跳過前 N 筆（預設 0，搭配 limit 分頁）",
    ])


def _apply_listing_formatter(i):
    return (
        f"- {i.get('Company', 'N/A')} ({i.get('Code', 'N/A')}): "
        f"申請日期 {i.get('ApplicationDate', 'N/A')}, 核准日期 {i.get('ApprovedDate', 'N/A')}, "
        f"上市日期 {i.get('ListingDate', 'N/A')}\n"
    )


# (endpoint, name, summary, label, empty_data_type, formatter)
LISTING_TOOLS = [
    (
        "/company/applylistingForeign", "get_foreign_companies_applying_for_listing",
        "查詢外國公司向證交所申請第一上市之公司。", "外國公司申請第一上市資料",
        "外國公司申請第一上市", _apply_listing_formatter,
    ),
    (
        "/company/newlisting", "get_recently_listed_companies",
        "查詢最近上市公司。", "最近上市公司資料", "最近上市公司",
        lambda i: f"- {i.get('Company', 'N/A')} ({i.get('Code', 'N/A')}): 上市日期 {i.get('ListingDate', 'N/A')}\n",
    ),
    (
        "/company/suspendListingCsvAndHtml", "get_suspended_listed_companies",
        "查詢終止上市公司。", "終止上市公司資料", "終止上市公司",
        lambda i: f"- {i.get('Company', 'N/A')} ({i.get('Code', 'N/A')}): 終止日期 {i.get('DelistingDate', 'N/A')}\n",
    ),
    (
        "/company/applylistingLocal", "get_local_companies_applying_for_listing",
        "查詢申請上市之本國公司。", "申請上市之本國公司資料",
        "申請上市之本國公司", _apply_listing_formatter,
    ),
]


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    """Register company listing tools with the MCP instance."""

    for endpoint, name, summary, label, empty_type, formatter in LISTING_TOOLS:
        create_list_tool(
            mcp, endpoint, name, _doc(summary), label, empty_type,
            formatter, filter_field="Company", client=client,
        )
