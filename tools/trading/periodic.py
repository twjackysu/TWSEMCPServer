"""Periodic trading data tools (monthly, yearly)."""

from typing import Optional
from fastmcp import FastMCP
from utils import (
    TWSEAPIClient,
    format_properties_with_values_multiline,
    MSG_NO_DATA_FOR_CODE,
    handle_api_errors,
)

def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    """Register periodic trading tools with the MCP instance."""
    
    # Use injected client or fallback to singleton
    _client = client or TWSEAPIClient.get_instance()
    
    @mcp.tool
    @handle_api_errors(use_code_param=True)
    def get_stock_monthly_average(code: str) -> str:
        """根據股票代號查詢上市個股日收盤價及月平均價。"""
        data = _client.fetch_company_data("/exchangeReport/STOCK_DAY_AVG_ALL", code)
        return format_properties_with_values_multiline(data) if data else ""

    @mcp.tool
    @handle_api_errors(use_code_param=True)
    def get_stock_monthly_trading(code: str) -> str:
        """根據股票代號查詢上市個股月成交資訊。

        回傳資訊包含月份、代號、名稱、最高價、最低價、加權平均價、成交筆數、成交金額、成交股數、週轉率。
        """
        data = _client.fetch_company_data("/exchangeReport/FMSRFK_ALL", code)
        if not data:
            return MSG_NO_DATA_FOR_CODE.format(query_target=f"股票代號 {code}", data_type="月成交資訊")
        
        result = f"【{data.get('Name', 'N/A')} ({data.get('Code', code)})】月成交資訊\n\n"
        
        month = data.get("Month", "N/A")
        highest = data.get("HighestPrice", "N/A")
        lowest = data.get("LowestPrice", "N/A")
        avg_price = data.get("WeightedAvgPriceAB", "N/A")
        transaction = data.get("Transaction", "N/A")
        trade_value = data.get("TradeValueA", "N/A")
        trade_volume = data.get("TradeVolumeB", "N/A")
        turnover = data.get("TurnoverRatio", "N/A")
        
        result += f"月份: {month}\n"
        result += f"最高價: {highest}\n"
        result += f"最低價: {lowest}\n"
        result += f"加權平均價: {avg_price}\n"
        result += f"成交筆數: {transaction}\n"
        result += f"成交金額: {trade_value}\n"
        result += f"成交股數: {trade_volume}\n"
        result += f"週轉率(%): {turnover}\n"
        
        return result

    @mcp.tool
    @handle_api_errors(use_code_param=True)
    def get_stock_yearly_trading(code: str) -> str:
        """根據股票代號查詢上市個股年成交資訊。

        回傳資訊包含年度、代號、名稱、成交股數、成交金額、成交筆數、最高價及日期、最低價及日期、收盤均價。
        """
        data = _client.fetch_company_data("/exchangeReport/FMNPTK_ALL", code)
        if not data:
            return MSG_NO_DATA_FOR_CODE.format(query_target=f"股票代號 {code}", data_type="年成交資訊")
        
        result = f"【{data.get('Name', 'N/A')} ({data.get('Code', code)})】年成交資訊\n\n"
        
        year = data.get("Year", "N/A")
        trade_volume = data.get("TradeVolume", "N/A")
        trade_value = data.get("TradeValue", "N/A")
        transaction = data.get("Transaction", "N/A")
        highest = data.get("HighestPrice", "N/A")
        h_date = data.get("HDate", "N/A")
        lowest = data.get("LowestPrice", "N/A")
        l_date = data.get("LDate", "N/A")
        avg_closing = data.get("AvgClosingPrice", "N/A")
        
        result += f"年度: {year}\n"
        result += f"成交股數: {trade_volume}\n"
        result += f"成交金額: {trade_value}\n"
        result += f"成交筆數: {transaction}\n"
        result += f"最高價: {highest} (日期: {h_date})\n"
        result += f"最低價: {lowest} (日期: {l_date})\n"
        result += f"平均收盤價: {avg_closing}\n"
        
        return result