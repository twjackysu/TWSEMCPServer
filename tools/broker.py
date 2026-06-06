"""Broker tools for TWSE data."""

from typing import Optional
from fastmcp import FastMCP
from utils import TWSEAPIClient, create_list_tool, create_simple_list_formatter


def _doc(summary: str, name_hint: Optional[str] = None) -> str:
    """Build a broker tool docstring, optionally with a ``name`` argument line."""
    lines = [summary, "", "        Args:"]
    if name_hint is not None:
        lines.append(f"            name: {name_hint}")
    lines.append("            limit: 回傳筆數上限（預設 50）")
    lines.append("            offset: 跳過前 N 筆（預設 0，搭配 limit 分頁）")
    return "\n".join(lines)


# (endpoint, name, summary, label, empty_data_type, filter_field, name_hint, formatter)
BROKER_TOOLS = [
    (
        "/opendata/t187ap01", "get_broker_service_personnel",
        "查詢券商業務別人員數。", "券商業務別人員數資料", "券商業務別人員數",
        None, None,
        lambda i: f"- {i.get('職位', 'N/A')}: 總人數 {i.get('合計', 'N/A')} (受託買賣 {i.get('受託買賣', 'N/A')}, 自行買賣 {i.get('自行買賣', 'N/A')})\n",
    ),
    (
        "/opendata/t187ap20", "get_broker_monthly_statements",
        "查詢各券商每月月計表。", "券商每月月計表資料", "券商每月月計表",
        "券商名稱", '券商名稱關鍵字（選填），例如 "遠智" 只回傳名稱含該字串的券商',
        lambda i: f"- {i.get('券商名稱', 'N/A')} ({i.get('券商代號', 'N/A')}) [{i.get('出表日期', 'N/A')}] {i.get('會計科目名稱', 'N/A')}: {i.get('借方餘額', 'N/A')}\n",
    ),
    (
        "/opendata/t187ap21", "get_broker_income_expenditure",
        "查詢各券商收支概況表資料。", "券商收支概況表資料", "券商收支概況表",
        "券商名稱", "券商名稱關鍵字（選填）",
        lambda i: f"- {i.get('券商名稱', 'N/A')} ({i.get('券商代號', 'N/A')}) [{i.get('出表日期', 'N/A')}] {i.get('會計科目名稱', 'N/A')}: {i.get('本月金額', 'N/A')}\n",
    ),
    (
        "/opendata/t187ap18", "get_broker_basic_info",
        "查詢證券商基本資料。", "證券商基本資料", "證券商基本",
        "券商(證券IB)簡稱", '券商簡稱關鍵字（選填），例如 "元大"',
        create_simple_list_formatter("券商(證券IB)簡稱", "證券代號", "設立日期"),
    ),
    (
        "/opendata/t187ap19", "get_broker_electronic_trading_statistics",
        "查詢電子式交易統計資訊。", "電子式交易統計資訊", "電子式交易統計",
        None, None,
        lambda i: f"- [{i.get('出表日期', 'N/A')}] 月份 {i.get('成交月份', 'N/A')}: 總成交筆數 {i.get('公司總成交筆數', 'N/A')}, 電子式成交筆數 {i.get('成交筆數', 'N/A')}\n",
    ),
    (
        "/opendata/OpenData_BRK01", "get_broker_gender_statistics",
        "查詢證券商營業員男女人數統計資料。", "證券商營業員男女人數統計資料", "證券商營業員男女人數統計",
        None, None,
        lambda i: f"- 券商代號 {i.get('證券商代號', 'N/A')}: 男 {i.get('男性員工人數', 'N/A')} 人, 女 {i.get('女性員工人數', 'N/A')} 人, 總計 {i.get('總人數', 'N/A')} 人\n",
    ),
    (
        "/opendata/OpenData_BRK02", "get_broker_branch_info",
        "查詢證券商分公司基本資料。", "證券商分公司基本資料", "證券商分公司基本",
        "證券商名稱", '券商名稱關鍵字（選填），例如 "富邦"',
        lambda i: f"- {i.get('證券商名稱', 'N/A')} ({i.get('證券商代號', 'N/A')}): {i.get('地址', 'N/A')}, 電話 {i.get('電話', 'N/A')}\n",
    ),
    (
        "/brokerService/secRegData", "get_brokers_offering_regular_investment",
        "查詢開辦定期定額業務證券商名單。", "開辦定期定額業務證券商", "開辦定期定額業務證券商名單",
        "Name", "券商名稱關鍵字（選填）",
        lambda i: f"- {i.get('Name', 'N/A')} ({i.get('SecuritiesFirmCode', 'N/A')}): 經紀業務 {i.get('BrokerageBusinessStartingDate', 'N/A')}, 財富管理 {i.get('WealthManagementBusinessStartingDate', 'N/A')}\n",
    ),
    (
        "/brokerService/brokerList", "get_broker_headquarters_info",
        "查詢證券商總公司基本資料。", "證券商總公司基本資料", "證券商總公司基本",
        "Name", "券商名稱關鍵字（選填）",
        lambda i: f"- {i.get('Name', 'N/A')} ({i.get('Code', 'N/A')}): 設立 {i.get('EstablishmentDate', 'N/A')}, 地址 {i.get('Address', 'N/A')}, 電話 {i.get('Telephone', 'N/A')}\n",
    ),
]


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    """Register broker tools with the MCP instance."""

    for endpoint, name, summary, label, empty_type, filter_field, name_hint, formatter in BROKER_TOOLS:
        create_list_tool(
            mcp, endpoint, name, _doc(summary, name_hint), label, empty_type,
            formatter, filter_field=filter_field, client=client,
        )
