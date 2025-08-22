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
    def get_twse_news(start_date: str = "", end_date: str = "") -> str:
        """
        Get latest news from Taiwan Stock Exchange with optional date filtering.
        
        Retrieves official news announcements from TWSE including market updates,
        regulatory changes, system maintenance notices, and other important 
        information for market participants.
        
        Args:
            start_date: Start date for filtering news (format: YYYYMMDD, e.g., "20250101")
                       If empty, defaults to current month's first day
            end_date: End date for filtering news (format: YYYYMMDD, e.g., "20250131")
                     If empty, defaults to current month's last day
        
        Note: 
            - If both dates are empty, returns current month's news
            - Date format must be YYYYMMDD (e.g., "20250822" for August 22, 2025)
            - API returns news in Chinese with dates in format YYYMMDD (民國年)
        
        Returns:
            Formatted string containing TWSE news including:
            - Title (標題)
            - URL/Link (連結)
            - Date (日期) - in format YYYMMDD (民國年)
        """
        try:
            from datetime import datetime, date
            import calendar
            
            # If no dates provided, use current month
            if not start_date and not end_date:
                now = datetime.now()
                # Convert to 民國年 format (subtract 1911 years)
                roc_year = now.year - 1911
                start_date = f"{roc_year:03d}{now.month:02d}01"
                
                # Get last day of current month
                last_day = calendar.monthrange(now.year, now.month)[1]
                end_date = f"{roc_year:03d}{now.month:02d}{last_day:02d}"
            elif start_date and not end_date:
                # If only start_date provided, convert to 民國年 and use same month
                if len(start_date) == 8:  # YYYYMMDD format
                    year = int(start_date[:4]) - 1911
                    month = start_date[4:6]
                    day = start_date[6:8]
                    start_date = f"{year:03d}{month}{day}"
                    
                    # Set end_date to last day of that month
                    orig_year = int(start_date[:4]) + 1911 if len(start_date) == 7 else int(start_date[:3]) + 1911
                    orig_month = int(start_date[3:5]) if len(start_date) == 7 else int(start_date[3:5])
                    last_day = calendar.monthrange(orig_year, orig_month)[1]
                    end_date = f"{year:03d}{month}{last_day:02d}"
            elif not start_date and end_date:
                # If only end_date provided, convert to 民國年 and use same month start
                if len(end_date) == 8:  # YYYYMMDD format
                    year = int(end_date[:4]) - 1911
                    month = end_date[4:6]
                    day = end_date[6:8]
                    end_date = f"{year:03d}{month}{day}"
                    start_date = f"{year:03d}{month}01"
            else:
                # Both dates provided, convert both to 民國年 format
                if len(start_date) == 8:  # YYYYMMDD format
                    year = int(start_date[:4]) - 1911
                    start_date = f"{year:03d}{start_date[4:]}"
                if len(end_date) == 8:  # YYYYMMDD format
                    year = int(end_date[:4]) - 1911
                    end_date = f"{year:03d}{end_date[4:]}"
            
            # Get all news data
            data = TWSEAPIClient.get_data("/news/newsList")
            
            # Filter by date range if dates are provided
            if data and (start_date or end_date):
                filtered_data = []
                for item in data:
                    if isinstance(item, dict) and 'Date' in item:
                        item_date = str(item['Date'])
                        if start_date and end_date:
                            if start_date <= item_date <= end_date:
                                filtered_data.append(item)
                        elif start_date:
                            if item_date >= start_date:
                                filtered_data.append(item)
                        elif end_date:
                            if item_date <= end_date:
                                filtered_data.append(item)
                data = filtered_data
            
            return format_multiple_records(data) if data else ""
        except Exception:
            return ""

    @mcp.tool
    def get_twse_events(top: int = 10) -> str:
        """
        Get Taiwan Stock Exchange event announcements and activities.
        
        Retrieves information about TWSE organized events, seminars, training sessions,
        and other activities that may be of interest to market participants and investors.
        
        Args:
            top: Number of top events to return (default: 10). If empty or 0, returns all events.
        
        Returns:
            Formatted string containing TWSE events including:
            - Event number (No)
            - Event title/subject (活動主題)
            - Event details (詳細內容)
        """
        try:
            data = TWSEAPIClient.get_data("/news/eventList")
            if data and top > 0:
                data = data[:top]
            return format_multiple_records(data) if data else ""
        except Exception:
            return ""