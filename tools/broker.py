"""Broker tools for TWSE data."""

from utils import (
    TWSEAPIClient,
    DEFAULT_DISPLAY_LIMIT,
    MSG_NO_DATA,
    MSG_QUERY_FAILED,
    MSG_TOTAL_RECORDS,
    MSG_MORE_RECORDS,
    handle_api_errors,
)

def register_tools(mcp):
    """Register broker tools with the MCP instance."""
    
    @mcp.tool
    @handle_api_errors(data_type="券商業務別人員數")
    def get_broker_service_personnel() -> str:
        """Get personnel numbers by service type for brokers."""
        data = TWSEAPIClient.get_data("/opendata/t187ap01")
        if not data:
            return MSG_NO_DATA.format(data_type="券商業務別人員數")
        
        result = MSG_TOTAL_RECORDS.format(count=len(data), data_type="券商業務別人員數資料") + "\n\n"
        for item in data[:DEFAULT_DISPLAY_LIMIT]:
            broker_code = item.get("券商代號", "N/A")
            broker_name = item.get("券商名稱", "N/A")
            total_personnel = item.get("總人數", "N/A")
            result += f"- {broker_name} ({broker_code}): {total_personnel} 人\n"
        
        if len(data) > DEFAULT_DISPLAY_LIMIT:
            result += MSG_MORE_RECORDS.format(count=len(data) - DEFAULT_DISPLAY_LIMIT)
        
        return result

    @mcp.tool
    @handle_api_errors(data_type="券商每月月計表")
    def get_broker_monthly_statements() -> str:
        """Get monthly statements for brokers."""
        data = TWSEAPIClient.get_data("/opendata/t187ap20")
        if not data:
            return MSG_NO_DATA.format(data_type="券商每月月計表")
        
        result = MSG_TOTAL_RECORDS.format(count=len(data), data_type="券商每月月計表資料") + "\n\n"
        for item in data[:DEFAULT_DISPLAY_LIMIT]:
            broker_code = item.get("券商代號", "N/A")
            broker_name = item.get("券商名稱", "N/A")
            month = item.get("月份", "N/A")
            result += f"- {broker_name} ({broker_code}): {month}\n"
        
        if len(data) > DEFAULT_DISPLAY_LIMIT:
            result += MSG_MORE_RECORDS.format(count=len(data) - DEFAULT_DISPLAY_LIMIT)
        
        return result

    @mcp.tool
    @handle_api_errors(data_type="券商收支概況表")
    def get_broker_income_expenditure() -> str:
        """Get income and expenditure overview for brokers."""
        data = TWSEAPIClient.get_data("/opendata/t187ap21")
        if not data:
            return MSG_NO_DATA.format(data_type="券商收支概況表")
        
        result = MSG_TOTAL_RECORDS.format(count=len(data), data_type="券商收支概況表資料") + "\n\n"
        for item in data[:DEFAULT_DISPLAY_LIMIT]:
            broker_code = item.get("券商代號", "N/A")
            broker_name = item.get("券商名稱", "N/A")
            period = item.get("期間", "N/A")
            result += f"- {broker_name} ({broker_code}): {period}\n"
        
        if len(data) > DEFAULT_DISPLAY_LIMIT:
            result += MSG_MORE_RECORDS.format(count=len(data) - DEFAULT_DISPLAY_LIMIT)
        
        return result

    @mcp.tool
    @handle_api_errors(data_type="證券商基本")
    def get_broker_basic_info() -> str:
        """Get basic information for brokers."""
        data = TWSEAPIClient.get_data("/opendata/t187ap18")
        if not data:
            return MSG_NO_DATA.format(data_type="證券商基本")
        
        result = MSG_TOTAL_RECORDS.format(count=len(data), data_type="證券商基本資料") + "\n\n"
        for item in data[:DEFAULT_DISPLAY_LIMIT]:
            broker_code = item.get("券商代號", "N/A")
            broker_name = item.get("券商名稱", "N/A")
            establishment_date = item.get("設立日期", "N/A")
            result += f"- {broker_name} ({broker_code}): 設立日期 {establishment_date}\n"
        
        if len(data) > DEFAULT_DISPLAY_LIMIT:
            result += MSG_MORE_RECORDS.format(count=len(data) - DEFAULT_DISPLAY_LIMIT)
        
        return result

    @mcp.tool
    @handle_api_errors(data_type="電子式交易統計")
    def get_broker_electronic_trading_statistics() -> str:
        """Get electronic trading statistics."""
        data = TWSEAPIClient.get_data("/opendata/t187ap19")
        if not data:
            return MSG_NO_DATA.format(data_type="電子式交易統計")
        
        result = MSG_TOTAL_RECORDS.format(count=len(data), data_type="電子式交易統計資訊") + "\n\n"
        for item in data[:DEFAULT_DISPLAY_LIMIT]:
            date = item.get("日期", "N/A")
            total_volume = item.get("總成交量", "N/A")
            electronic_volume = item.get("電子式成交量", "N/A")
            result += f"- {date}: 總成交量 {total_volume}, 電子式成交量 {electronic_volume}\n"
        
        if len(data) > DEFAULT_DISPLAY_LIMIT:
            result += MSG_MORE_RECORDS.format(count=len(data) - DEFAULT_DISPLAY_LIMIT)
        
        return result

    @mcp.tool
    @handle_api_errors(data_type="證券商營業員男女人數統計")
    def get_broker_gender_statistics() -> str:
        """Get broker personnel gender statistics."""
        data = TWSEAPIClient.get_data("/opendata/OpenData_BRK01")
        if not data:
            return MSG_NO_DATA.format(data_type="證券商營業員男女人數統計")
        
        result = MSG_TOTAL_RECORDS.format(count=len(data), data_type="證券商營業員男女人數統計資料") + "\n\n"
        for item in data[:DEFAULT_DISPLAY_LIMIT]:
            broker_code = item.get("券商代號", "N/A")
            broker_name = item.get("券商名稱", "N/A")
            male_count = item.get("男營業員人數", "N/A")
            female_count = item.get("女營業員人數", "N/A")
            result += f"- {broker_name} ({broker_code}): 男 {male_count} 人, 女 {female_count} 人\n"
        
        if len(data) > DEFAULT_DISPLAY_LIMIT:
            result += MSG_MORE_RECORDS.format(count=len(data) - DEFAULT_DISPLAY_LIMIT)
        
        return result

    @mcp.tool
    @handle_api_errors(data_type="證券商分公司基本")
    def get_broker_branch_info() -> str:
        """Get broker branch office basic information."""
        data = TWSEAPIClient.get_data("/opendata/OpenData_BRK02")
        if not data:
            return MSG_NO_DATA.format(data_type="證券商分公司基本")
        
        result = MSG_TOTAL_RECORDS.format(count=len(data), data_type="證券商分公司基本資料") + "\n\n"
        for item in data[:DEFAULT_DISPLAY_LIMIT]:
            branch_code = item.get("分公司代號", "N/A")
            branch_name = item.get("分公司名稱", "N/A")
            broker_name = item.get("總公司名稱", "N/A")
            result += f"- {branch_name} ({branch_code}): 隸屬 {broker_name}\n"
        
        if len(data) > DEFAULT_DISPLAY_LIMIT:
            result += MSG_MORE_RECORDS.format(count=len(data) - DEFAULT_DISPLAY_LIMIT)
        
        return result

    @mcp.tool
    @handle_api_errors(data_type="開辦定期定額業務證券商名單")
    def get_brokers_offering_regular_investment() -> str:
        """Get list of brokers offering regular investment services."""
        data = TWSEAPIClient.get_data("/brokerService/secRegData")
        if not data:
            return MSG_NO_DATA.format(data_type="開辦定期定額業務證券商名單")
        
        result = MSG_TOTAL_RECORDS.format(count=len(data), data_type="開辦定期定額業務證券商") + "\n\n"
        for item in data[:DEFAULT_DISPLAY_LIMIT]:
            broker_code = item.get("券商代號", "N/A")
            broker_name = item.get("券商名稱", "N/A")
            service_start_date = item.get("開辦日期", "N/A")
            result += f"- {broker_name} ({broker_code}): 開辦日期 {service_start_date}\n"
        
        if len(data) > DEFAULT_DISPLAY_LIMIT:
            result += MSG_MORE_RECORDS.format(count=len(data) - DEFAULT_DISPLAY_LIMIT)
        
        return result

    @mcp.tool
    @handle_api_errors(data_type="證券商總公司基本")
    def get_broker_headquarters_info() -> str:
        """Get basic information of broker headquarters."""
        data = TWSEAPIClient.get_data("/brokerService/brokerList")
        if not data:
            return MSG_NO_DATA.format(data_type="證券商總公司基本")
        
        result = MSG_TOTAL_RECORDS.format(count=len(data), data_type="證券商總公司基本資料") + "\n\n"
        for item in data[:DEFAULT_DISPLAY_LIMIT]:
            broker_code = item.get("券商代號", "N/A")
            broker_name = item.get("券商名稱", "N/A")
            establishment_date = item.get("設立日期", "N/A")
            capital = item.get("資本額", "N/A")
            result += f"- {broker_name} ({broker_code}): 設立日期 {establishment_date}, 資本額 {capital}\n"
        
        if len(data) > DEFAULT_DISPLAY_LIMIT:
            result += MSG_MORE_RECORDS.format(count=len(data) - DEFAULT_DISPLAY_LIMIT)
        
        return result