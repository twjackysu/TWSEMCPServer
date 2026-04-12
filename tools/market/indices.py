"""Market indices tools."""

from typing import Optional
from fastmcp import FastMCP
from utils import TWSEAPIClient, format_properties_with_values_multiline, format_multiple_records, MSG_QUERY_FAILED

def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    """Register market indices tools with the MCP instance."""
    
    # Use injected client or fallback to singleton
    _client = client or TWSEAPIClient.get_instance()
    
    @mcp.tool
    def get_market_index_info(category: str = "major", count: int = 20, output_format: str = "detailed") -> str:
        """查詢每日收盤行情-大盤統計資訊。

        Args:
            category: 指數分類篩選：
                - "major": 主要市場指數（加權、台50、中型100等）
                - "sector": 產業類指數（電子類、金融類等）
                - "esg": ESG永續相關指數
                - "leverage": 槓桿及反向指數
                - "return": 報酬指數（含股息再投資）
                - "thematic": 主題指數（AI、5G、電動車等）
                - "dividend": 高股息相關指數
                - "all": 所有指數
            count: 回傳筆數上限（預設20，非all分類最大50）
            output_format: 輸出格式：
                - "detailed": 詳細格式（所有欄位）
                - "summary": 摘要格式（指數名稱、收盤價、漲跌%）
                - "simple": 簡單格式（僅名稱和漲跌%）
        """
        try:
            data = _client.fetch_latest_market_data("/exchangeReport/MI_INDEX")
            if not data:
                return ""
            
            # Filter data based on category using pattern matching
            filtered_data = []
            def index_name(item):
                return item.get("指數", "")
            
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
            
            # Format output based on output_format parameter
            if not result_data:
                return f"No indices found for category: {category}"
            
            if output_format == "simple":
                # Simple output_format: just name and change percentage
                lines = []
                for item in result_data:
                    name = item.get("指數", "")
                    change_pct = item.get("漲跌百分比", "")
                    direction = item.get("漲跌", "")
                    lines.append(f"{name}: {direction}{change_pct}%")
                return "\n".join(lines)
                
            elif output_format == "summary":
                # Summary output_format: name, close price, change percentage
                lines = []
                for item in result_data:
                    name = item.get("指數", "")
                    close = item.get("收盤指數", "")
                    change_pct = item.get("漲跌百分比", "")
                    direction = item.get("漲跌", "")
                    lines.append(f"{name}: {close} 點 ({direction}{change_pct}%)")
                return "\n".join(lines)
                
            else:  # detailed output_format (default)
                return format_multiple_records(result_data)
            
        except Exception as e:
            return MSG_QUERY_FAILED.format(error=str(e))

    @mcp.tool
    def get_market_historical_index() -> str:
        """查詢發行量加權股價指數歷史資料。"""
        try:
            data = _client.fetch_latest_market_data("/indicesReport/MI_5MINS_HIST", count=20)
            return format_multiple_records(data)
        except Exception as e:
            return MSG_QUERY_FAILED.format(error=str(e))

    @mcp.tool
    def get_taiwan_island_index_history() -> str:
        """查詢寶島股價指數歷史資料。"""
        try:
            data = _client.fetch_latest_market_data("/indicesReport/FRMSA", count=20)
            return format_multiple_records(data)
        except Exception as e:
            return MSG_QUERY_FAILED.format(error=str(e))

    @mcp.tool
    def get_taiwan_50_index_history() -> str:
        """查詢臺灣50指數歷史資料。"""
        try:
            data = _client.fetch_latest_market_data("/indicesReport/TAI50I", count=20)
            return format_multiple_records(data)
        except Exception as e:
            return MSG_QUERY_FAILED.format(error=str(e))

    @mcp.tool
    def get_taiwan_total_return_index() -> str:
        """查詢發行量加權股價報酬指數。"""
        try:
            data = _client.fetch_latest_market_data("/indicesReport/MFI94U", count=20)
            return format_multiple_records(data)
        except Exception as e:
            return MSG_QUERY_FAILED.format(error=str(e))