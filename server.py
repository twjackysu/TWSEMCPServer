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

@mcp.prompt
def stock_trend_analysis_prompt(stock_symbol: str, period: str) -> PromptMessage:
    """Prompt for Taiwan stock trend analysis using TWSE OpenAPI endpoints."""
    return twse_stock_trend_prompt(stock_symbol, period)

def format_properties_with_values_multiline(data: dict) -> str:
    description_items = [f"{key}: {value}" for key, value in data.items()]
    description = "\n".join(description_items)
    return description

if __name__ == "__main__":
    mcp.run(transport='stdio')