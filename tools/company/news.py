"""News and major announcements related tools for Taiwan Stock Exchange MCP server."""

from utils import TWSEAPIClient, format_multiple_records, format_properties_with_values_multiline


def register_tools(mcp):
    @mcp.tool
    def get_company_major_news(code: str = "") -> str:
        """
        Get daily major announcements from listed companies.
        
        Retrieves important company announcements and material information disclosures
        that may impact stock prices and investor decisions. Can filter by company code
        or get all announcements.
        
        Args:
            code: Company stock code (optional). If provided, filters results for specific company.
                 If empty, returns all major announcements.
        
        Returns:
            Formatted string containing major announcements including:
            - Report date (出表日期)
            - Announcement date (發言日期) 
            - Announcement time (發言時間)
            - Company code (公司代號)
            - Company name (公司名稱)
            - Subject/Title (主旨)
            - Applicable regulations (符合條款)
            - Event occurrence date (事實發生日)
            - Description/Details (說明)
        """
        try:
            if code:
                data = TWSEAPIClient.get_company_data("/opendata/t187ap04_L", code)
                return format_properties_with_values_multiline(data) if data else ""
            else:
                data = TWSEAPIClient.get_data("/opendata/t187ap04_L")
                return format_multiple_records(data) if data else ""
        except Exception:
            return ""

    @mcp.tool
    def get_twse_news() -> str:
        """
        Get latest news from Taiwan Stock Exchange.
        
        Retrieves official news announcements from TWSE including market updates,
        regulatory changes, system maintenance notices, and other important 
        information for market participants.
        
        Returns:
            Formatted string containing TWSE news including:
            - Title (標題)
            - URL/Link (連結)
            - Date (日期)
        """
        try:
            data = TWSEAPIClient.get_data("/news/newsList")
            return format_multiple_records(data) if data else ""
        except Exception:
            return ""

    @mcp.tool
    def get_twse_events() -> str:
        """
        Get Taiwan Stock Exchange event announcements and activities.
        
        Retrieves information about TWSE organized events, seminars, training sessions,
        and other activities that may be of interest to market participants and investors.
        
        Returns:
            Formatted string containing TWSE events including:
            - Event number (No)
            - Event title/subject (活動主題)
            - Event details (詳細內容)
        """
        try:
            data = TWSEAPIClient.get_data("/news/eventList")
            return format_multiple_records(data) if data else ""
        except Exception:
            return ""