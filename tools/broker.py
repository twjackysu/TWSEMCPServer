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

    _client = client or TWSEAPIClient.get_instance()

    @mcp.tool
    @handle_api_errors(data_type="券商業務別人員數")
    def get_broker_service_personnel(limit: int = 50, offset: int = 0) -> str:
        """查詢券商業務別人員數。

        Args:
            limit: 回傳筆數上限（預設 50）
            offset: 跳過前 N 筆（預設 0，搭配 limit 分頁）
        """
        data = _client.fetch_data("/opendata/t187ap01")
        if not data:
            return MSG_NO_DATA.format(data_type="券商業務別人員數")

        def formatter(item):
            position = item.get("職位", "N/A")
            total = item.get("合計", "N/A")
            trading = item.get("受託買賣", "N/A")
            self_trading = item.get("自行買賣", "N/A")
            return f"- {position}: 總人數 {total} (受託買賣 {trading}, 自行買賣 {self_trading})\n"

        return format_list_response(data, "券商業務別人員數資料", formatter, limit=limit, offset=offset)

    @mcp.tool
    @handle_api_errors(data_type="券商每月月計表")
    def get_broker_monthly_statements(name: str = "", limit: int = 50, offset: int = 0) -> str:
        """查詢各券商每月月計表。

        Args:
            name: 券商名稱關鍵字（選填），例如 "遠智" 只回傳名稱含該字串的券商
            limit: 回傳筆數上限（預設 50）
            offset: 跳過前 N 筆（預設 0，搭配 limit 分頁）
        """
        data = _client.fetch_data("/opendata/t187ap20")
        if not data:
            return MSG_NO_DATA.format(data_type="券商每月月計表")

        if name:
            data = [d for d in data if name in d.get("券商名稱", "")]

        def formatter(item: Dict[str, str]) -> str:
            broker_name = item.get("券商名稱", "N/A")
            code = item.get("券商代號", "N/A")
            date = item.get("出表日期", "N/A")
            subject = item.get("會計科目名稱", "N/A")
            debit = item.get("借方餘額", "N/A")
            return f"- {broker_name} ({code}) [{date}] {subject}: {debit}\n"

        return format_list_response(data, "券商每月月計表資料", formatter, limit=limit, offset=offset)

    @mcp.tool
    @handle_api_errors(data_type="券商收支概況表")
    def get_broker_income_expenditure(name: str = "", limit: int = 50, offset: int = 0) -> str:
        """查詢各券商收支概況表資料。

        Args:
            name: 券商名稱關鍵字（選填）
            limit: 回傳筆數上限（預設 50）
            offset: 跳過前 N 筆（預設 0，搭配 limit 分頁）
        """
        data = _client.fetch_data("/opendata/t187ap21")
        if not data:
            return MSG_NO_DATA.format(data_type="券商收支概況表")

        if name:
            data = [d for d in data if name in d.get("券商名稱", "")]

        def formatter(item: Dict[str, str]) -> str:
            broker_name = item.get("券商名稱", "N/A")
            code = item.get("券商代號", "N/A")
            date = item.get("出表日期", "N/A")
            subject = item.get("會計科目名稱", "N/A")
            amount = item.get("本月金額", "N/A")
            return f"- {broker_name} ({code}) [{date}] {subject}: {amount}\n"

        return format_list_response(data, "券商收支概況表資料", formatter, limit=limit, offset=offset)

    @mcp.tool
    @handle_api_errors(data_type="證券商基本")
    def get_broker_basic_info(name: str = "", limit: int = 50, offset: int = 0) -> str:
        """查詢證券商基本資料。

        Args:
            name: 券商簡稱關鍵字（選填），例如 "元大"
            limit: 回傳筆數上限（預設 50）
            offset: 跳過前 N 筆（預設 0，搭配 limit 分頁）
        """
        data = _client.fetch_data("/opendata/t187ap18")
        if not data:
            return MSG_NO_DATA.format(data_type="證券商基本")

        if name:
            data = [d for d in data if name in d.get("券商(證券IB)簡稱", "")]

        formatter = create_simple_list_formatter("券商(證券IB)簡稱", "證券代號", "設立日期")
        return format_list_response(data, "證券商基本資料", formatter, limit=limit, offset=offset)

    @mcp.tool
    @handle_api_errors(data_type="電子式交易統計")
    def get_broker_electronic_trading_statistics(limit: int = 50, offset: int = 0) -> str:
        """查詢電子式交易統計資訊。

        Args:
            limit: 回傳筆數上限（預設 50）
            offset: 跳過前 N 筆（預設 0，搭配 limit 分頁）
        """
        data = _client.fetch_data("/opendata/t187ap19")
        if not data:
            return MSG_NO_DATA.format(data_type="電子式交易統計")

        def formatter(item: Dict[str, str]) -> str:
            date = item.get("出表日期", "N/A")
            month = item.get("成交月份", "N/A")
            total_trades = item.get("公司總成交筆數", "N/A")
            electronic_trades = item.get("成交筆數", "N/A")
            return f"- [{date}] 月份 {month}: 總成交筆數 {total_trades}, 電子式成交筆數 {electronic_trades}\n"

        return format_list_response(data, "電子式交易統計資訊", formatter, limit=limit, offset=offset)

    @mcp.tool
    @handle_api_errors(data_type="證券商營業員男女人數統計")
    def get_broker_gender_statistics(limit: int = 50, offset: int = 0) -> str:
        """查詢證券商營業員男女人數統計資料。

        Args:
            limit: 回傳筆數上限（預設 50）
            offset: 跳過前 N 筆（預設 0，搭配 limit 分頁）
        """
        data = _client.fetch_data("/opendata/OpenData_BRK01")
        if not data:
            return MSG_NO_DATA.format(data_type="證券商營業員男女人數統計")

        def formatter(item: Dict[str, str]) -> str:
            broker_code = item.get("證券商代號", "N/A")
            male_count = item.get("男性員工人數", "N/A")
            female_count = item.get("女性員工人數", "N/A")
            total = item.get("總人數", "N/A")
            return f"- 券商代號 {broker_code}: 男 {male_count} 人, 女 {female_count} 人, 總計 {total} 人\n"

        return format_list_response(data, "證券商營業員男女人數統計資料", formatter, limit=limit, offset=offset)

    @mcp.tool
    @handle_api_errors(data_type="證券商分公司基本")
    def get_broker_branch_info(name: str = "", limit: int = 50, offset: int = 0) -> str:
        """查詢證券商分公司基本資料。

        Args:
            name: 券商名稱關鍵字（選填），例如 "富邦"
            limit: 回傳筆數上限（預設 50）
            offset: 跳過前 N 筆（預設 0，搭配 limit 分頁）
        """
        data = _client.fetch_data("/opendata/OpenData_BRK02")
        if not data:
            return MSG_NO_DATA.format(data_type="證券商分公司基本")

        if name:
            data = [d for d in data if name in d.get("證券商名稱", "")]

        def formatter(item: Dict[str, str]) -> str:
            code = item.get("證券商代號", "N/A")
            broker_name = item.get("證券商名稱", "N/A")
            address = item.get("地址", "N/A")
            phone = item.get("電話", "N/A")
            return f"- {broker_name} ({code}): {address}, 電話 {phone}\n"

        return format_list_response(data, "證券商分公司基本資料", formatter, limit=limit, offset=offset)

    @mcp.tool
    @handle_api_errors(data_type="開辦定期定額業務證券商名單")
    def get_brokers_offering_regular_investment(name: str = "", limit: int = 50, offset: int = 0) -> str:
        """查詢開辦定期定額業務證券商名單。

        Args:
            name: 券商名稱關鍵字（選填）
            limit: 回傳筆數上限（預設 50）
            offset: 跳過前 N 筆（預設 0，搭配 limit 分頁）
        """
        data = _client.fetch_data("/brokerService/secRegData")
        if not data:
            return MSG_NO_DATA.format(data_type="開辦定期定額業務證券商名單")

        if name:
            data = [d for d in data if name in d.get("Name", "")]

        def formatter(item: Dict[str, str]) -> str:
            code = item.get("SecuritiesFirmCode", "N/A")
            broker_name = item.get("Name", "N/A")
            start_date = item.get("BrokerageBusinessStartingDate", "N/A")
            wealth_date = item.get("WealthManagementBusinessStartingDate", "N/A")
            return f"- {broker_name} ({code}): 經紀業務 {start_date}, 財富管理 {wealth_date}\n"

        return format_list_response(data, "開辦定期定額業務證券商", formatter, limit=limit, offset=offset)

    @mcp.tool
    @handle_api_errors(data_type="證券商總公司基本")
    def get_broker_headquarters_info(name: str = "", limit: int = 50, offset: int = 0) -> str:
        """查詢證券商總公司基本資料。

        Args:
            name: 券商名稱關鍵字（選填）
            limit: 回傳筆數上限（預設 50）
            offset: 跳過前 N 筆（預設 0，搭配 limit 分頁）
        """
        data = _client.fetch_data("/brokerService/brokerList")
        if not data:
            return MSG_NO_DATA.format(data_type="證券商總公司基本")

        if name:
            data = [d for d in data if name in d.get("Name", "")]

        def formatter(item: Dict[str, str]) -> str:
            code = item.get("Code", "N/A")
            broker_name = item.get("Name", "N/A")
            establishment_date = item.get("EstablishmentDate", "N/A")
            address = item.get("Address", "N/A")
            phone = item.get("Telephone", "N/A")
            return f"- {broker_name} ({code}): 設立 {establishment_date}, 地址 {address}, 電話 {phone}\n"

        return format_list_response(data, "證券商總公司基本資料", formatter, limit=limit, offset=offset)
