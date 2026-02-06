"""Company listing related tools."""

from typing import Optional
from fastmcp import FastMCP
from utils import TWSEAPIClient

def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    """Register company listing tools with the MCP instance."""
    
    @mcp.tool
    def get_foreign_companies_applying_for_listing() -> str:
        """Get foreign companies applying for first listing on TWSE."""
        try:
            data = TWSEAPIClient.get_data("/company/applylistingForeign")
            if not data:
                return "目前沒有外國公司申請第一上市資料。"
            
            result = f"共有 {len(data)} 筆外國公司申請第一上市資料：\n\n"
            for item in data[:20]:  # Limit to first 20 for readability
                code = item.get("Code", "N/A")
                company_name = item.get("Company", "N/A")
                application_date = item.get("ApplicationDate", "N/A")
                approved_date = item.get("ApprovedDate", "N/A")
                listing_date = item.get("ListingDate", "N/A")
                result += f"- {company_name} ({code}): 申請日期 {application_date}, 核准日期 {approved_date}, 上市日期 {listing_date}\n"
            
            if len(data) > 20:
                result += f"\n... 還有 {len(data) - 20} 筆資料"
            
            return result
        except Exception as e:
            return f"查詢失敗: {str(e)}"

    @mcp.tool
    def get_recently_listed_companies() -> str:
        """Get recently listed companies."""
        try:
            data = TWSEAPIClient.get_data("/company/newlisting")
            if not data:
                return "目前沒有最近上市公司資料。"
            
            result = f"共有 {len(data)} 筆最近上市公司資料：\n\n"
            for item in data[:20]:  # Limit to first 20 for readability
                company_code = item.get("Code", "N/A")
                company_name = item.get("Company", "N/A")
                listing_date = item.get("ListingDate", "N/A")
                result += f"- {company_name} ({company_code}): 上市日期 {listing_date}\n"
            
            if len(data) > 20:
                result += f"\n... 還有 {len(data) - 20} 筆資料"
            
            return result
        except Exception as e:
            return f"查詢失敗: {str(e)}"

    @mcp.tool
    def get_suspended_listed_companies() -> str:
        """Get companies whose listing has been suspended."""
        try:
            data = TWSEAPIClient.get_data("/company/suspendListingCsvAndHtml")
            if not data:
                return "目前沒有終止上市公司資料。"
            
            result = f"共有 {len(data)} 筆終止上市公司資料：\n\n"
            for item in data[:20]:  # Limit to first 20 for readability
                company_code = item.get("Code", "N/A")
                company_name = item.get("Company", "N/A")
                delisting_date = item.get("DelistingDate", "N/A")
                result += f"- {company_name} ({company_code}): 終止日期 {delisting_date}\n"
            
            if len(data) > 20:
                result += f"\n... 還有 {len(data) - 20} 筆資料"
            
            return result
        except Exception as e:
            return f"查詢失敗: {str(e)}"

    @mcp.tool
    def get_local_companies_applying_for_listing() -> str:
        """Get local companies applying for listing."""
        try:
            data = TWSEAPIClient.get_data("/company/applylistingLocal")
            if not data:
                return "目前沒有申請上市之本國公司資料。"
            
            result = f"共有 {len(data)} 筆申請上市之本國公司資料：\n\n"
            for item in data[:20]:  # Limit to first 20 for readability
                code = item.get("Code", "N/A")
                company_name = item.get("Company", "N/A")
                application_date = item.get("ApplicationDate", "N/A")
                approved_date = item.get("ApprovedDate", "N/A")
                listing_date = item.get("ListingDate", "N/A")
                result += f"- {company_name} ({code}): 申請日期 {application_date}, 核准日期 {approved_date}, 上市日期 {listing_date}\n"
            
            if len(data) > 20:
                result += f"\n... 還有 {len(data) - 20} 筆資料"
            
            return result
        except Exception as e:
            return f"查詢失敗: {str(e)}"