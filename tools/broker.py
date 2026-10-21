"""Broker tools for TWSE data."""

from typing import List, Optional
from fastmcp import FastMCP
from utils import TWSEAPIClient, create_simple_list_formatter
from toolkit import ListToolSpec, create_list_tool


BROKER_TOOLS: List[ListToolSpec] = [
    ListToolSpec(
        endpoint="/opendata/t187ap01", name="get_broker_service_personnel",
        summary="查詢券商業務別人員數。",
        label="券商業務別人員數資料", empty_data_type="券商業務別人員數",
        formatter=lambda i: f"- {i.get('職位', 'N/A')}: 總人數 {i.get('合計', 'N/A')} (受託買賣 {i.get('受託買賣', 'N/A')}, 自行買賣 {i.get('自行買賣', 'N/A')})\n",
    ),
    ListToolSpec(
        endpoint="/opendata/t187ap20", name="get_broker_monthly_statements",
        summary="查詢各券商每月月計表。",
        label="券商每月月計表資料", empty_data_type="券商每月月計表",
        filter_field="券商名稱", name_hint='券商名稱關鍵字（選填），例如 "遠智" 只回傳名稱含該字串的券商',
        formatter=lambda i: f"- {i.get('券商名稱', 'N/A')} ({i.get('券商代號', 'N/A')}) [{i.get('出表日期', 'N/A')}] {i.get('會計科目名稱', 'N/A')}: {i.get('借方餘額', 'N/A')}\n",
    ),
    ListToolSpec(
        endpoint="/opendata/t187ap21", name="get_broker_income_expenditure",
        summary="查詢各券商收支概況表資料。",
        label="券商收支概況表資料", empty_data_type="券商收支概況表",
        filter_field="券商名稱", name_hint="券商名稱關鍵字（選填）",
        formatter=lambda i: f"- {i.get('券商名稱', 'N/A')} ({i.get('券商代號', 'N/A')}) [{i.get('出表日期', 'N/A')}] {i.get('會計科目名稱', 'N/A')}: {i.get('本月金額', 'N/A')}\n",
    ),
    ListToolSpec(
        endpoint="/opendata/t187ap18", name="get_broker_basic_info",
        summary="查詢證券商基本資料。",
        label="證券商基本資料", empty_data_type="證券商基本",
        filter_field="券商(證券IB)簡稱", name_hint='券商簡稱關鍵字（選填），例如 "元大"',
        formatter=create_simple_list_formatter("券商(證券IB)簡稱", "證券代號", "設立日期"),
    ),
    ListToolSpec(
        endpoint="/opendata/t187ap19", name="get_broker_electronic_trading_statistics",
        summary="查詢電子式交易統計資訊。",
        label="電子式交易統計資訊", empty_data_type="電子式交易統計",
        formatter=lambda i: f"- [{i.get('出表日期', 'N/A')}] 月份 {i.get('成交月份', 'N/A')}: 總成交筆數 {i.get('公司總成交筆數', 'N/A')}, 電子式成交筆數 {i.get('成交筆數', 'N/A')}\n",
    ),
    ListToolSpec(
        endpoint="/opendata/OpenData_BRK01", name="get_broker_gender_statistics",
        summary="查詢證券商營業員男女人數統計資料。",
        label="證券商營業員男女人數統計資料", empty_data_type="證券商營業員男女人數統計",
        formatter=lambda i: f"- 券商代號 {i.get('證券商代號', 'N/A')}: 男 {i.get('男性員工人數', 'N/A')} 人, 女 {i.get('女性員工人數', 'N/A')} 人, 總計 {i.get('總人數', 'N/A')} 人\n",
    ),
    ListToolSpec(
        endpoint="/opendata/OpenData_BRK02", name="get_broker_branch_info",
        summary="查詢證券商分公司基本資料。",
        label="證券商分公司基本資料", empty_data_type="證券商分公司基本",
        filter_field="證券商名稱", name_hint='券商名稱關鍵字（選填），例如 "富邦"',
        formatter=lambda i: f"- {i.get('證券商名稱', 'N/A')} ({i.get('證券商代號', 'N/A')}): {i.get('地址', 'N/A')}, 電話 {i.get('電話', 'N/A')}\n",
    ),
    ListToolSpec(
        endpoint="/brokerService/secRegData", name="get_brokers_offering_regular_investment",
        summary="查詢開辦定期定額業務證券商名單。",
        label="開辦定期定額業務證券商", empty_data_type="開辦定期定額業務證券商名單",
        filter_field="Name", name_hint="券商名稱關鍵字（選填）",
        formatter=lambda i: f"- {i.get('Name', 'N/A')} ({i.get('SecuritiesFirmCode', 'N/A')}): 經紀業務 {i.get('BrokerageBusinessStartingDate', 'N/A')}, 財富管理 {i.get('WealthManagementBusinessStartingDate', 'N/A')}\n",
    ),
    ListToolSpec(
        endpoint="/brokerService/brokerList", name="get_broker_headquarters_info",
        summary="查詢證券商總公司基本資料。",
        label="證券商總公司基本資料", empty_data_type="證券商總公司基本",
        filter_field="Name", name_hint="券商名稱關鍵字（選填）",
        formatter=lambda i: f"- {i.get('Name', 'N/A')} ({i.get('Code', 'N/A')}): 設立 {i.get('EstablishmentDate', 'N/A')}, 地址 {i.get('Address', 'N/A')}, 電話 {i.get('Telephone', 'N/A')}\n",
    ),
]


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    """Register broker tools with the MCP instance."""

    for spec in BROKER_TOOLS:
        create_list_tool(mcp, spec, client)
