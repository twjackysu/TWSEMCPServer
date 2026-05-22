"""Company listing related tools."""

from typing import Optional
from fastmcp import FastMCP
from utils import (
    TWSEAPIClient,
    MSG_NO_DATA,
    handle_api_errors,
    format_list_response,
)

def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    """Register company listing tools with the MCP instance."""

    _client = client or TWSEAPIClient.get_instance()

    @mcp.tool
    @handle_api_errors(data_type="外國公司申請第一上市")
    def get_foreign_companies_applying_for_listing(name: str = "", limit: int = 50, offset: int = 0) -> str:
        """查詢外國公司向證交所申請第一上市之公司。

        Args:
            name: 公司名稱關鍵字（選填）
            limit: 回傳筆數上限（預設 50）
            offset: 跳過前 N 筆（預設 0，搭配 limit 分頁）
        """
        data = _client.fetch_data("/company/applylistingForeign")
        if not data:
            return MSG_NO_DATA.format(data_type="外國公司申請第一上市")

        if name:
            data = [d for d in data if name in d.get("Company", "")]

        def formatter(item):
            code = item.get("Code", "N/A")
            company_name = item.get("Company", "N/A")
            application_date = item.get("ApplicationDate", "N/A")
            approved_date = item.get("ApprovedDate", "N/A")
            listing_date = item.get("ListingDate", "N/A")
            return f"- {company_name} ({code}): 申請日期 {application_date}, 核准日期 {approved_date}, 上市日期 {listing_date}\n"

        return format_list_response(data, "外國公司申請第一上市資料", formatter, limit=limit, offset=offset)

    @mcp.tool
    @handle_api_errors(data_type="最近上市公司")
    def get_recently_listed_companies(name: str = "", limit: int = 50, offset: int = 0) -> str:
        """查詢最近上市公司。

        Args:
            name: 公司名稱關鍵字（選填）
            limit: 回傳筆數上限（預設 50）
            offset: 跳過前 N 筆（預設 0，搭配 limit 分頁）
        """
        data = _client.fetch_data("/company/newlisting")
        if not data:
            return MSG_NO_DATA.format(data_type="最近上市公司")

        if name:
            data = [d for d in data if name in d.get("Company", "")]

        def formatter(item):
            company_code = item.get("Code", "N/A")
            company_name = item.get("Company", "N/A")
            listing_date = item.get("ListingDate", "N/A")
            return f"- {company_name} ({company_code}): 上市日期 {listing_date}\n"

        return format_list_response(data, "最近上市公司資料", formatter, limit=limit, offset=offset)

    @mcp.tool
    @handle_api_errors(data_type="終止上市公司")
    def get_suspended_listed_companies(name: str = "", limit: int = 50, offset: int = 0) -> str:
        """查詢終止上市公司。

        Args:
            name: 公司名稱關鍵字（選填）
            limit: 回傳筆數上限（預設 50）
            offset: 跳過前 N 筆（預設 0，搭配 limit 分頁）
        """
        data = _client.fetch_data("/company/suspendListingCsvAndHtml")
        if not data:
            return MSG_NO_DATA.format(data_type="終止上市公司")

        if name:
            data = [d for d in data if name in d.get("Company", "")]

        def formatter(item):
            company_code = item.get("Code", "N/A")
            company_name = item.get("Company", "N/A")
            delisting_date = item.get("DelistingDate", "N/A")
            return f"- {company_name} ({company_code}): 終止日期 {delisting_date}\n"

        return format_list_response(data, "終止上市公司資料", formatter, limit=limit, offset=offset)

    @mcp.tool
    @handle_api_errors(data_type="申請上市之本國公司")
    def get_local_companies_applying_for_listing(name: str = "", limit: int = 50, offset: int = 0) -> str:
        """查詢申請上市之本國公司。

        Args:
            name: 公司名稱關鍵字（選填）
            limit: 回傳筆數上限（預設 50）
            offset: 跳過前 N 筆（預設 0，搭配 limit 分頁）
        """
        data = _client.fetch_data("/company/applylistingLocal")
        if not data:
            return MSG_NO_DATA.format(data_type="申請上市之本國公司")

        if name:
            data = [d for d in data if name in d.get("Company", "")]

        def formatter(item):
            code = item.get("Code", "N/A")
            company_name = item.get("Company", "N/A")
            application_date = item.get("ApplicationDate", "N/A")
            approved_date = item.get("ApprovedDate", "N/A")
            listing_date = item.get("ListingDate", "N/A")
            return f"- {company_name} ({code}): 申請日期 {application_date}, 核准日期 {approved_date}, 上市日期 {listing_date}\n"

        return format_list_response(data, "申請上市之本國公司資料", formatter, limit=limit, offset=offset)
