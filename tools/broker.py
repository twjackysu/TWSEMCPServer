"""Broker tools for TWSE data."""

from typing import Dict, Optional
from fastmcp import FastMCP
from utils import (
    TWSEAPIClient,
    MSG_NO_DATA,
    handle_api_errors,
    format_list_response,
    create_simple_list_formatter,
)

def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    """Register broker tools with the MCP instance."""
    
    # Use injected client or fallback to singleton
    _client = client or TWSEAPIClient.get_instance()
    
    @mcp.tool
    @handle_api_errors(data_type="券商業務別人員數")
    def get_broker_service_personnel() -> str:
        """Get personnel numbers by service type for brokers."""
        data = _client.fetch_data("/opendata/t187ap01")
        if not data:
            return MSG_NO_DATA.format(data_type="券商業務別人員數")
        
        def formatter(item):
            position = item.get("職位", "N/A")
            total = item.get("合計", "N/A")
            trading = item.get("受託買賣", "N/A")
            self_trading = item.get("自行買賣", "N/A")
            return f"- {position}: 總人數 {total} (受託買賣 {trading}, 自行買賣 {self_trading})\n"
        
        return format_list_response(data, "券商業務別人員數資料", formatter)

    @mcp.tool
    @handle_api_errors(data_type="券商每月月計表")
    def get_broker_monthly_statements() -> str:
        """Get monthly statements for brokers."""
        data = _client.fetch_data("/opendata/t187ap20")
        if not data:
            return MSG_NO_DATA.format(data_type="券商每月月計表")
        
        def formatter(item: Dict[str, str]) -> str:
            name = item.get("券商名稱", "N/A")
            code = item.get("券商代號", "N/A")
            date = item.get("出表日期", "N/A")
            subject = item.get("會計科目名稱", "N/A")
            debit = item.get("借方餘額", "N/A")
            return f"- {name} ({code}) [{date}] {subject}: {debit}\n"
        
        return format_list_response(data, "券商每月月計表資料", formatter)

    @mcp.tool
    @handle_api_errors(data_type="券商收支概況表")
    def get_broker_income_expenditure() -> str:
        """Get income and expenditure overview for brokers."""
        data = _client.fetch_data("/opendata/t187ap21")
        if not data:
            return MSG_NO_DATA.format(data_type="券商收支概況表")
        
        def formatter(item: Dict[str, str]) -> str:
            name = item.get("券商名稱", "N/A")
            code = item.get("券商代號", "N/A")
            date = item.get("出表日期", "N/A")
            subject = item.get("會計科目名稱", "N/A")
            amount = item.get("本月金額", "N/A")
            return f"- {name} ({code}) [{date}] {subject}: {amount}\n"
        
        return format_list_response(data, "券商收支概況表資料", formatter)

    @mcp.tool
    @handle_api_errors(data_type="證券商基本")
    def get_broker_basic_info() -> str:
        """Get basic information for brokers."""
        data = _client.fetch_data("/opendata/t187ap18")
        if not data:
            return MSG_NO_DATA.format(data_type="證券商基本")
        
        formatter = create_simple_list_formatter("券商(證券IB)簡稱", "證券代號", "設立日期")
        return format_list_response(data, "證券商基本資料", formatter)

    @mcp.tool
    @handle_api_errors(data_type="電子式交易統計")
    def get_broker_electronic_trading_statistics() -> str:
        """Get electronic trading statistics."""
        data = _client.fetch_data("/opendata/t187ap19")
        if not data:
            return MSG_NO_DATA.format(data_type="電子式交易統計")
        
        def formatter(item: Dict[str, str]) -> str:
            date = item.get("出表日期", "N/A")
            month = item.get("成交月份", "N/A")
            total_trades = item.get("公司總成交筆數", "N/A")
            electronic_trades = item.get("成交筆數", "N/A")
            return f"- [{date}] 月份 {month}: 總成交筆數 {total_trades}, 電子式成交筆數 {electronic_trades}\n"
        
        return format_list_response(data, "電子式交易統計資訊", formatter)

    @mcp.tool
    @handle_api_errors(data_type="證券商營業員男女人數統計")
    def get_broker_gender_statistics() -> str:
        """Get broker personnel gender statistics."""
        data = _client.fetch_data("/opendata/OpenData_BRK01")
        if not data:
            return MSG_NO_DATA.format(data_type="證券商營業員男女人數統計")
        
        def formatter(item: Dict[str, str]) -> str:
            broker_code = item.get("證券商代號", "N/A")
            male_count = item.get("男性員工人數", "N/A")
            female_count = item.get("女性員工人數", "N/A")
            total = item.get("總人數", "N/A")
            return f"- 券商代號 {broker_code}: 男 {male_count} 人, 女 {female_count} 人, 總計 {total} 人\n"
        
        return format_list_response(data, "證券商營業員男女人數統計資料", formatter)

    @mcp.tool
    @handle_api_errors(data_type="證券商分公司基本")
    def get_broker_branch_info() -> str:
        """Get broker branch office basic information."""
        data = _client.fetch_data("/opendata/OpenData_BRK02")
        if not data:
            return MSG_NO_DATA.format(data_type="證券商分公司基本")
        
        def formatter(item: Dict[str, str]) -> str:
            code = item.get("證券商代號", "N/A")
            name = item.get("證券商名稱", "N/A")
            address = item.get("地址", "N/A")
            phone = item.get("電話", "N/A")
            return f"- {name} ({code}): {address}, 電話 {phone}\n"
        
        return format_list_response(data, "證券商分公司基本資料", formatter)

    @mcp.tool
    @handle_api_errors(data_type="開辦定期定額業務證券商名單")
    def get_brokers_offering_regular_investment() -> str:
        """Get list of brokers offering regular investment services."""
        data = _client.fetch_data("/brokerService/secRegData")
        if not data:
            return MSG_NO_DATA.format(data_type="開辦定期定額業務證券商名單")
        
        def formatter(item: Dict[str, str]) -> str:
            code = item.get("SecuritiesFirmCode", "N/A")
            name = item.get("Name", "N/A")
            start_date = item.get("BrokerageBusinessStartingDate", "N/A")
            wealth_date = item.get("WealthManagementBusinessStartingDate", "N/A")
            return f"- {name} ({code}): 經紀業務 {start_date}, 財富管理 {wealth_date}\n"
        
        return format_list_response(data, "開辦定期定額業務證券商", formatter)

    @mcp.tool
    @handle_api_errors(data_type="證券商總公司基本")
    def get_broker_headquarters_info() -> str:
        """Get basic information of broker headquarters."""
        data = _client.fetch_data("/brokerService/brokerList")
        if not data:
            return MSG_NO_DATA.format(data_type="證券商總公司基本")
        
        def formatter(item: Dict[str, str]) -> str:
            code = item.get("Code", "N/A")
            name = item.get("Name", "N/A")
            establishment_date = item.get("EstablishmentDate", "N/A")
            address = item.get("Address", "N/A")
            phone = item.get("Telephone", "N/A")
            return f"- {name} ({code}): 設立 {establishment_date}, 地址 {address}, 電話 {phone}\n"
        
        return format_list_response(data, "證券商總公司基本資料", formatter)