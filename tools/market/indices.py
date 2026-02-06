"""Market indices tools."""

from typing import Optional
from fastmcp import FastMCP
from utils import TWSEAPIClient, format_properties_with_values_multiline, format_multiple_records

def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    """Register market indices tools with the MCP instance."""
    
    # Use injected client or fallback to singleton
    _client = client or TWSEAPIClient.get_instance()
    
    @mcp.tool
    def get_market_index_info(category: str = "major", count: int = 20, format: str = "detailed") -> str:
        """Obtain daily market closing information and overall market statistics.
        
        Args:
            category: Index category to filter by:
                - "major": Major market indices (主要市場指數: 加權、台50、中型100等)
                - "sector": Industry sector indices (產業類指數: 電子類、金融類等)
                - "esg": ESG and sustainability indices (ESG永續相關指數)
                - "leverage": Leveraged and inverse indices (槓桿及反向指數)
                - "return": Total return indices (報酬指數: 含股息再投資)
                - "thematic": Thematic indices (主題指數: AI、5G、電動車等)
                - "dividend": High dividend indices (高股息相關指數)
                - "all": All indices (所有指數)
            count: Maximum number of indices to return (default: 20, max: 50 for non-all categories)
            format: Output format:
                - "detailed": Full details with all fields (詳細格式)
                - "summary": Compact summary with key info only (摘要格式: 指數名稱、收盤價、漲跌%)
                - "simple": Just index name and change percentage (簡單格式: 僅名稱和漲跌%)
        """
        try:
            data = _client.fetch_latest_market_data("/exchangeReport/MI_INDEX")
            if not data:
                return ""
            
            # Filter data based on category using pattern matching
            filtered_data = []
            index_name = lambda item: item.get("指數", "")
            
            if category == "major":
                # Major indices: Core market benchmarks (非產業別、非報酬指數、非槓桿指數)
                filtered_data = [item for item in data 
                               if not any(pattern in index_name(item) for pattern in ["類指數", "報酬指數", "兩倍", "反向", "槓桿"])
                               and any(pattern in index_name(item) for pattern in [
                                   "發行量加權", "寶島", "臺灣50", "中型", "小型", "未含", "公司治理", "高股息"
                               ])]
                
            elif category == "sector":
                # Industry sector indices: Anything with "類指數" but not return indices
                filtered_data = [item for item in data 
                               if "類指數" in index_name(item) 
                               and "報酬指數" not in index_name(item)]
                
            elif category == "esg":
                # ESG and sustainability indices: Pattern-based matching
                esg_patterns = ["ESG", "永續", "公司治理", "社會責任", "環境", "綠能", "低碳", "友善"]
                filtered_data = [item for item in data 
                               if any(pattern in index_name(item) for pattern in esg_patterns)]
                
            elif category == "leverage":
                # Leveraged and inverse indices: Pattern-based matching
                leverage_patterns = ["兩倍", "反向", "槓桿"]
                filtered_data = [item for item in data 
                               if any(pattern in index_name(item) for pattern in leverage_patterns)]
                
            elif category == "return":
                # Total return indices: Any index with "報酬指數"
                filtered_data = [item for item in data 
                               if "報酬指數" in index_name(item)]
                
            elif category == "thematic":
                # Thematic indices: Special themed indices (AI, 5G, biotech, etc.)
                thematic_patterns = ["AI", "5G", "生技", "電動車", "綠能", "半導體", "科技", "創新"]
                filtered_data = [item for item in data 
                               if any(pattern in index_name(item) for pattern in thematic_patterns)
                               and "報酬指數" not in index_name(item)]
                
            elif category == "dividend":
                # High dividend focused indices
                dividend_patterns = ["高股息", "高息", "股息", "股利", "優息", "存股"]
                filtered_data = [item for item in data 
                               if any(pattern in index_name(item) for pattern in dividend_patterns)
                               and "報酬指數" not in index_name(item)]
                
            else:  # category == "all" or invalid category
                filtered_data = data
                
            # Limit the number of results
            if category != "all":
                count = min(count, 50)  # Cap at 50 for specific categories
            
            result_data = filtered_data[:count] if count > 0 else filtered_data
            
            # Format output based on format parameter
            if not result_data:
                return f"No indices found for category: {category}"
            
            if format == "simple":
                # Simple format: just name and change percentage
                lines = []
                for item in result_data:
                    name = item.get("指數", "")
                    change_pct = item.get("漲跌百分比", "")
                    direction = item.get("漲跌", "")
                    lines.append(f"{name}: {direction}{change_pct}%")
                return "\n".join(lines)
                
            elif format == "summary":
                # Summary format: name, close price, change percentage
                lines = []
                for item in result_data:
                    name = item.get("指數", "")
                    close = item.get("收盤指數", "")
                    change_pct = item.get("漲跌百分比", "")
                    direction = item.get("漲跌", "")
                    lines.append(f"{name}: {close} 點 ({direction}{change_pct}%)")
                return "\n".join(lines)
                
            else:  # detailed format (default)
                return format_multiple_records(result_data)
            
        except Exception:
            return ""

    @mcp.tool
    def get_market_historical_index() -> str:
        """Obtain historical TAIEX (Taiwan Capitalization Weighted Stock Index) data for long-term trend analysis."""
        try:
            data = _client.fetch_latest_market_data("/indicesReport/MI_5MINS_HIST", count=20)
            return format_multiple_records(data)
        except Exception:
            return ""

    @mcp.tool
    def get_taiwan_island_index_history() -> str:
        """Obtain historical data for Taiwan Island Stock Price Index."""
        try:
            data = _client.fetch_latest_market_data("/indicesReport/FRMSA", count=20)
            return format_multiple_records(data)
        except Exception:
            return ""

    @mcp.tool
    def get_taiwan_50_index_history() -> str:
        """Obtain historical data for Taiwan 50 Index."""
        try:
            data = _client.fetch_latest_market_data("/indicesReport/TAI50I", count=20)
            return format_multiple_records(data)
        except Exception:
            return ""

    @mcp.tool
    def get_taiwan_total_return_index() -> str:
        """Obtain Taiwan Capitalization Weighted Stock Price Return Index."""
        try:
            data = _client.fetch_latest_market_data("/indicesReport/MFI94U", count=20)
            return format_multiple_records(data)
        except Exception:
            return ""