from fastmcp import FastMCP
import requests
from fastmcp.prompts.prompt import PromptMessage
import logging

from prompts.twse_stock_trend_prompt import twse_stock_trend_prompt

# Configure logging (similar to .NET ILogger)
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

mcp = FastMCP("TWSE Stock Trend Analysis 🚀")

USER_AGENT = "stock-mcp/1.0"
BASE_URL = "https://openapi.twse.com.tw/v1"

@mcp.tool
def get_company_profile(code: str) -> str:
    """Obtain the basic information of a listed company as a JSON string object based on its stock code."""
    url = f"{BASE_URL}/opendata/t187ap03_L"
    logger.info(f"Fetching TWSE company profile data from {url}")
    try:
        # 透過 verify=False 跳過 SSL 憑證驗證
        resp = requests.get(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"}, verify=False, timeout=30.0)
        resp.raise_for_status()
        
        # 設定正確的編碼 (UTF-8)
        resp.encoding = 'utf-8'
        data = resp.json()
        filteredData = [item for item in data if isinstance(item, dict) and item.get("公司代號") == code]
        firstOrDefaultItem = filteredData[0] if filteredData else None
        formattedData = format_properties_with_values_multiline(firstOrDefaultItem) if firstOrDefaultItem else {}
        return formattedData
    except Exception as e:
        logger.error(f"Failed to fetch company profiles: {e}")
        return ''



@mcp.tool
def get_company_dividend(code: str) -> str:
    """Obtain the dividend distribution information of a listed company based on its stock code."""
    url = f"{BASE_URL}/opendata/t187ap45_L"
    logger.info(f"Fetching TWSE company dividend data from {url}")
    try:
        # 透過 verify=False 跳過 SSL 憑證驗證
        resp = requests.get(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"}, verify=False, timeout=30.0)
        resp.raise_for_status()
        
        # 設定正確的編碼 (UTF-8)
        resp.encoding = 'utf-8'
        data = resp.json()
        filteredData = [item for item in data if isinstance(item, dict) and item.get("公司代號") == code]
        firstOrDefaultItem = filteredData[0] if filteredData else None
        formattedData = format_properties_with_values_multiline(firstOrDefaultItem) if firstOrDefaultItem else {}
        return formattedData
    except Exception as e:
        logger.error(f"Failed to fetch company dividend data: {e}")
        return ''



@mcp.tool
def get_company_monthly_revenue(code: str) -> str:
    """Obtain monthly revenue information for a listed company based on its stock code."""
    url = f"{BASE_URL}/opendata/t187ap05_L"
    logger.info(f"Fetching TWSE company monthly revenue data from {url}")
    try:
        # 透過 verify=False 跳過 SSL 憑證驗證
        resp = requests.get(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"}, verify=False, timeout=30.0)
        resp.raise_for_status()
        
        # 設定正確的編碼 (UTF-8)
        resp.encoding = 'utf-8'
        data = resp.json()
        filteredData = [item for item in data if isinstance(item, dict) and item.get("公司代號") == code]
        # 取得最近的資料
        firstOrDefaultItem = filteredData[0] if filteredData else None
        formattedData = format_properties_with_values_multiline(firstOrDefaultItem) if firstOrDefaultItem else {}
        return formattedData
    except Exception as e:
        logger.error(f"Failed to fetch company monthly revenue data: {e}")
        return ''

@mcp.tool
def get_company_governance_info(code: str) -> str:
    """Obtain corporate governance information for a listed company based on its stock code."""
    url = f"{BASE_URL}/opendata/t187ap46_L_9"
    logger.info(f"Fetching TWSE company governance data from {url}")
    try:
        # 透過 verify=False 跳過 SSL 憑證驗證
        resp = requests.get(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"}, verify=False, timeout=30.0)
        resp.raise_for_status()
        
        # 設定正確的編碼 (UTF-8)
        resp.encoding = 'utf-8'
        data = resp.json()
        filteredData = [item for item in data if isinstance(item, dict) and item.get("公司代號") == code]
        firstOrDefaultItem = filteredData[0] if filteredData else None
        formattedData = format_properties_with_values_multiline(firstOrDefaultItem) if firstOrDefaultItem else {}
        return formattedData
    except Exception as e:
        logger.error(f"Failed to fetch company governance data: {e}")
        return ''

@mcp.tool
def get_company_climate_management(code: str) -> str:
    """Obtain climate-related management information for a listed company based on its stock code."""
    url = f"{BASE_URL}/opendata/t187ap46_L_8"
    logger.info(f"Fetching TWSE company climate management data from {url}")
    try:
        # 透過 verify=False 跳過 SSL 憑證驗證
        resp = requests.get(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"}, verify=False, timeout=30.0)
        resp.raise_for_status()
        
        # 設定正確的編碼 (UTF-8)
        resp.encoding = 'utf-8'
        data = resp.json()
        filteredData = [item for item in data if isinstance(item, dict) and item.get("公司代號") == code]
        firstOrDefaultItem = filteredData[0] if filteredData else None
        formattedData = format_properties_with_values_multiline(firstOrDefaultItem) if firstOrDefaultItem else {}
        return formattedData
    except Exception as e:
        logger.error(f"Failed to fetch company climate management data: {e}")
        return ''

@mcp.tool
def get_company_risk_management(code: str) -> str:
    """Obtain risk management policy information for a listed company based on its stock code."""
    url = f"{BASE_URL}/opendata/t187ap46_L_19"
    logger.info(f"Fetching TWSE company risk management data from {url}")
    try:
        # 透過 verify=False 跳過 SSL 憑證驗證
        resp = requests.get(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"}, verify=False, timeout=30.0)
        resp.raise_for_status()
        
        # 設定正確的編碼 (UTF-8)
        resp.encoding = 'utf-8'
        data = resp.json()
        filteredData = [item for item in data if isinstance(item, dict) and item.get("公司代號") == code]
        firstOrDefaultItem = filteredData[0] if filteredData else None
        formattedData = format_properties_with_values_multiline(firstOrDefaultItem) if firstOrDefaultItem else {}
        return formattedData
    except Exception as e:
        logger.error(f"Failed to fetch company risk management data: {e}")
        return ''

@mcp.tool
def get_company_supply_chain_management(code: str) -> str:
    """Obtain supply chain management information for a listed company based on its stock code."""
    url = f"{BASE_URL}/opendata/t187ap46_L_13"
    logger.info(f"Fetching TWSE company supply chain management data from {url}")
    try:
        # 透過 verify=False 跳過 SSL 憑證驗證
        resp = requests.get(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"}, verify=False, timeout=30.0)
        resp.raise_for_status()
        
        # 設定正確的編碼 (UTF-8)
        resp.encoding = 'utf-8'
        data = resp.json()
        filteredData = [item for item in data if isinstance(item, dict) and item.get("公司代號") == code]
        firstOrDefaultItem = filteredData[0] if filteredData else None
        formattedData = format_properties_with_values_multiline(firstOrDefaultItem) if firstOrDefaultItem else {}
        return formattedData
    except Exception as e:
        logger.error(f"Failed to fetch company supply chain management data: {e}")
        return ''

@mcp.tool
def get_company_info_security(code: str) -> str:
    """Obtain information security data for a listed company based on its stock code."""
    url = f"{BASE_URL}/opendata/t187ap46_L_16"
    logger.info(f"Fetching TWSE company information security data from {url}")
    try:
        # 透過 verify=False 跳過 SSL 憑證驗證
        resp = requests.get(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"}, verify=False, timeout=30.0)
        resp.raise_for_status()
        
        # 設定正確的編碼 (UTF-8)
        resp.encoding = 'utf-8'
        data = resp.json()
        filteredData = [item for item in data if isinstance(item, dict) and item.get("公司代號") == code]
        firstOrDefaultItem = filteredData[0] if filteredData else None
        formattedData = format_properties_with_values_multiline(firstOrDefaultItem) if firstOrDefaultItem else {}
        return formattedData
    except Exception as e:
        logger.error(f"Failed to fetch company information security data: {e}")
        return ''



@mcp.prompt
def stock_trend_analysis_prompt(stock_symbol: str, period: str) -> PromptMessage:
    """Prompt for Taiwan stock trend analysis using TWSE OpenAPI endpoints."""
    return twse_stock_trend_prompt(stock_symbol, period)

def format_properties_with_values_multiline(data: dict) -> str:
    description_items = [f"{key}: {value}" for key, value in data.items()]
    description = "\n".join(description_items)
    return description

@mcp.tool
def get_stock_daily_trading(code: str) -> str:
    """Obtain daily trading information for a listed company stock based on its stock code."""
    url = f"{BASE_URL}/exchangeReport/STOCK_DAY_ALL"
    logger.info(f"Fetching TWSE stock daily trading data from {url}")
    try:
        # 透過 verify=False 跳過 SSL 憑證驗證
        resp = requests.get(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"}, verify=False, timeout=30.0)
        resp.raise_for_status()
        
        # 設定正確的編碼 (UTF-8)
        resp.encoding = 'utf-8'
        data = resp.json()
        filteredData = [item for item in data if isinstance(item, dict) and item.get("Code") == code]
        # 取得最近的交易資料
        firstOrDefaultItem = filteredData[0] if filteredData else None
        formattedData = format_properties_with_values_multiline(firstOrDefaultItem) if firstOrDefaultItem else {}
        return formattedData
    except Exception as e:
        logger.error(f"Failed to fetch stock daily trading data: {e}")
        return ''

@mcp.tool
def get_stock_monthly_average(code: str) -> str:
    """Obtain daily closing price and monthly average price for a listed company stock based on its stock code."""
    url = f"{BASE_URL}/exchangeReport/STOCK_DAY_AVG_ALL"
    logger.info(f"Fetching TWSE stock monthly average data from {url}")
    try:
        # 透過 verify=False 跳過 SSL 憑證驗證
        resp = requests.get(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"}, verify=False, timeout=30.0)
        resp.raise_for_status()
        
        # 設定正確的編碼 (UTF-8)
        resp.encoding = 'utf-8'
        data = resp.json()
        filteredData = [item for item in data if isinstance(item, dict) and item.get("Code") == code]
        firstOrDefaultItem = filteredData[0] if filteredData else None
        formattedData = format_properties_with_values_multiline(firstOrDefaultItem) if firstOrDefaultItem else {}
        return formattedData
    except Exception as e:
        logger.error(f"Failed to fetch stock monthly average data: {e}")
        return ''

@mcp.tool
def get_stock_valuation_ratios(code: str) -> str:
    """Obtain P/E ratio, dividend yield, and P/B ratio for a listed company stock based on its stock code."""
    url = f"{BASE_URL}/exchangeReport/BWIBBU_ALL"
    logger.info(f"Fetching TWSE stock valuation ratios data from {url}")
    try:
        # 透過 verify=False 跳過 SSL 憑證驗證
        resp = requests.get(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"}, verify=False, timeout=30.0)
        resp.raise_for_status()
        
        # 設定正確的編碼 (UTF-8)
        resp.encoding = 'utf-8'
        data = resp.json()
        filteredData = [item for item in data if isinstance(item, dict) and item.get("Code") == code]
        firstOrDefaultItem = filteredData[0] if filteredData else None
        formattedData = format_properties_with_values_multiline(firstOrDefaultItem) if firstOrDefaultItem else {}
        return formattedData
    except Exception as e:
        logger.error(f"Failed to fetch stock valuation ratios data: {e}")
        return ''

@mcp.tool
def get_market_index_info() -> str:
    """Obtain daily market closing information and overall market statistics."""
    url = f"{BASE_URL}/exchangeReport/MI_INDEX"
    logger.info(f"Fetching TWSE market index data from {url}")
    try:
        # 透過 verify=False 跳過 SSL 憑證驗證
        resp = requests.get(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"}, verify=False, timeout=30.0)
        resp.raise_for_status()
        
        # 設定正確的編碼 (UTF-8)
        resp.encoding = 'utf-8'
        data = resp.json()
        # 取得最近的市場資料
        firstOrDefaultItem = data[0] if data and isinstance(data, list) else None
        formattedData = format_properties_with_values_multiline(firstOrDefaultItem) if firstOrDefaultItem else {}
        return formattedData
    except Exception as e:
        logger.error(f"Failed to fetch market index data: {e}")
        return ''

@mcp.tool
def get_margin_trading_info() -> str:
    """Obtain margin trading and short selling balance information for the market."""
    url = f"{BASE_URL}/exchangeReport/MI_MARGN"
    logger.info(f"Fetching TWSE margin trading data from {url}")
    try:
        # 透過 verify=False 跳過 SSL 憑證驗證
        resp = requests.get(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"}, verify=False, timeout=30.0)
        resp.raise_for_status()
        
        # 設定正確的編碼 (UTF-8)
        resp.encoding = 'utf-8'
        data = resp.json()
        # 格式化融資融券資料
        formatted_items = []
        for item in data[:10]:  # 只取前10筆避免資料過多
            if isinstance(item, dict):
                formatted_item = format_properties_with_values_multiline(item)
                formatted_items.append(formatted_item)
                formatted_items.append("-" * 30)
        
        return "\n".join(formatted_items)
    except Exception as e:
        logger.error(f"Failed to fetch margin trading data: {e}")
        return ''

@mcp.tool
def get_stock_monthly_trading(code: str) -> str:
    """Obtain monthly trading information for a listed company stock based on its stock code."""
    url = f"{BASE_URL}/exchangeReport/FMSRFK_ALL"
    logger.info(f"Fetching TWSE stock monthly trading data from {url}")
    try:
        # 透過 verify=False 跳過 SSL 憑證驗證
        resp = requests.get(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"}, verify=False, timeout=30.0)
        resp.raise_for_status()
        
        # 設定正確的編碼 (UTF-8)
        resp.encoding = 'utf-8'
        data = resp.json()
        filteredData = [item for item in data if isinstance(item, dict) and item.get("Code") == code]
        # 取得最近的月成交資料
        firstOrDefaultItem = filteredData[0] if filteredData else None
        formattedData = format_properties_with_values_multiline(firstOrDefaultItem) if firstOrDefaultItem else {}
        return formattedData
    except Exception as e:
        logger.error(f"Failed to fetch stock monthly trading data: {e}")
        return ''

@mcp.tool
def get_stock_yearly_trading(code: str) -> str:
    """Obtain yearly trading information for a listed company stock based on its stock code."""
    url = f"{BASE_URL}/exchangeReport/FMNPTK_ALL"
    logger.info(f"Fetching TWSE stock yearly trading data from {url}")
    try:
        # 透過 verify=False 跳過 SSL 憑證驗證
        resp = requests.get(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"}, verify=False, timeout=30.0)
        resp.raise_for_status()
        
        # 設定正確的編碼 (UTF-8)
        resp.encoding = 'utf-8'
        data = resp.json()
        filteredData = [item for item in data if isinstance(item, dict) and item.get("Code") == code]
        # 取得最近的年成交資料
        firstOrDefaultItem = filteredData[0] if filteredData else None
        formattedData = format_properties_with_values_multiline(firstOrDefaultItem) if firstOrDefaultItem else {}
        return formattedData
    except Exception as e:
        logger.error(f"Failed to fetch stock yearly trading data: {e}")
        return ''

@mcp.tool
def get_company_income_statement(code: str) -> str:
    """Obtain comprehensive income statement for a listed company based on its stock code (general industry)."""
    url = f"{BASE_URL}/opendata/t187ap06_L_ci"
    logger.info(f"Fetching TWSE company income statement data from {url}")
    try:
        # 透過 verify=False 跳過 SSL 憑證驗證
        resp = requests.get(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"}, verify=False, timeout=30.0)
        resp.raise_for_status()
        
        # 設定正確的編碼 (UTF-8)
        resp.encoding = 'utf-8'
        data = resp.json()
        filteredData = [item for item in data if isinstance(item, dict) and item.get("公司代號") == code]
        # 取得最近的財報資料
        firstOrDefaultItem = filteredData[0] if filteredData else None
        formattedData = format_properties_with_values_multiline(firstOrDefaultItem) if firstOrDefaultItem else {}
        return formattedData
    except Exception as e:
        logger.error(f"Failed to fetch company income statement data: {e}")
        return ''

@mcp.tool
def get_company_balance_sheet(code: str) -> str:
    """Obtain balance sheet for a listed company based on its stock code (general industry)."""
    url = f"{BASE_URL}/opendata/t187ap07_L_ci"
    logger.info(f"Fetching TWSE company balance sheet data from {url}")
    try:
        # 透過 verify=False 跳過 SSL 憑證驗證
        resp = requests.get(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"}, verify=False, timeout=30.0)
        resp.raise_for_status()
        
        # 設定正確的編碼 (UTF-8)
        resp.encoding = 'utf-8'
        data = resp.json()
        filteredData = [item for item in data if isinstance(item, dict) and item.get("公司代號") == code]
        # 取得最近的資產負債表資料
        firstOrDefaultItem = filteredData[0] if filteredData else None
        formattedData = format_properties_with_values_multiline(firstOrDefaultItem) if firstOrDefaultItem else {}
        return formattedData
    except Exception as e:
        logger.error(f"Failed to fetch company balance sheet data: {e}")
        return ''

def format_properties_with_values_multiline(data: dict) -> str:
    description_items = [f"{key}: {value}" for key, value in data.items()]
    description = "\n".join(description_items)
    return description

if __name__ == "__main__":
    mcp.run(transport='stdio')