from fastmcp import FastMCP
import requests
import json
from fastmcp.prompts.prompt import PromptMessage
import logging

from prompts.twse_stock_trend_prompt import twse_stock_trend_prompt

# Configure logging (similar to .NET ILogger)
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

mcp = FastMCP("TWSE Stock Trend Analysis 🚀")

@mcp.tool
def json_type(data) -> str:
    """Return 'array' if input is a list, 'object' if input is a dict."""
    logger.info(f"json_type called with data type: {type(data)}")
    if isinstance(data, list):
        logger.info("Input is a list. Returning 'array'.")
        return "array"
    elif isinstance(data, dict):
        logger.info("Input is a dict. Returning 'object'.")
        return "object"
    else:
        logger.info("Input is neither list nor dict. Returning 'unknown'.")
        return "unknown"

@mcp.tool
def json_array_filter(json_array: list, key: str, value) -> list:
    """Return items in the JSON array where item[key] == value."""
    logger.info(f"json_array_filter called with key='{key}', value='{value}', array length={len(json_array) if isinstance(json_array, list) else 'N/A'}")
    if not isinstance(json_array, list):
        logger.warning("Input is not a list. Returning empty list.")
        return []
    filtered = [item for item in json_array if isinstance(item, dict) and item.get(key) == value]
    logger.info(f"Filtered result length: {len(filtered)}")
    return filtered

@mcp.tool
def fetch_json(url: str) -> str:
    """Fetch JSON from a URL and return response.json() string"""
    logger.info(f"fetch_json called with url: {url}")
    headers = {
        "Accept": "application/json"
    }
    try:
        # 先嘗試正常請求
        resp = requests.get(url, headers=headers)
        resp.raise_for_status()
    except requests.exceptions.SSLError:
        # 如果有 SSL 錯誤，改用不驗證 SSL 的方式
        logger.warning(f"SSL verification failed for {url}, trying with verify=False")
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        resp = requests.get(url, headers=headers, verify=False)
        resp.raise_for_status()
    
    if 'application/json' in resp.headers.get('Content-Type', ''):
        data = resp.json()
        logger.info("JSON data received successfully.")
        logger.debug(json.dumps(data, indent=2))
        return json.dumps(data, indent=2)
    else:
        logger.warning(f"Expected JSON, but received Content-Type: {resp.headers.get('Content-Type')}")
        logger.warning(f"Response content: {resp.text[:500]}")
    return ''

@mcp.tool
def parse_swagger(swagger_url: str) -> list:
    """Fetch a swagger.json and return a list of available APIs with method, endpoint, input schema, and output schema."""
    logger.info(f"parse_swagger called with swagger_url: {swagger_url}")
    resp = requests.get(swagger_url)
    resp.raise_for_status()
    swagger = resp.json()
    apis = []
    paths = swagger.get("paths", {})
    logger.info(f"Found {len(paths)} API paths in swagger.json.")
    for endpoint, methods in paths.items():
        for method, details in methods.items():
            input_schema = details.get("parameters", [])
            output_schema = details.get("responses", {})
            apis.append({
                "http_method": method.upper(),
                "endpoint": endpoint,
                "input_schema": input_schema,
                "output_schema": output_schema
            })
    logger.info(f"parse_swagger returning {len(apis)} API definitions.")
    return apis

@mcp.tool
def fetch_twse_company_profile() -> str:
    """Fetches the basic profile data for all listed companies from TWSE OpenAPI (t187ap03_L).
    output format:
    ```
    {
        "出表日期": "string",
        "公司代號": "string",
        "公司名稱": "string",
        "公司簡稱": "string",
        "外國企業註冊地國": "string",
        "產業別": "string",
        "住址": "string",
        "營利事業統一編號": "string",
        "董事長": "string",
        "總經理": "string",
        "發言人": "string",
        "發言人職稱": "string",
        "代理發言人": "string",
        "總機電話": "string",
        "成立日期": "string",
        "上市日期": "string",
        "普通股每股面額": "string",
        "實收資本額": "string",
        "私募股數": "string",
        "特別股": "string",
        "編制財務報表類型": "string",
        "股票過戶機構": "string",
        "過戶電話": "string",
        "過戶地址": "string",
        "簽證會計師事務所": "string",
        "簽證會計師1": "string",
        "簽證會計師2": "string",
        "英文簡稱": "string",
        "英文通訊地址": "string",
        "傳真機號碼": "string",
        "電子郵件信箱": "string",
        "網址": "string",
        "已發行普通股數或TDR原股發行股數": "string"
    }
    ```
    """
    url = "https://openapi.twse.com.tw/v1/opendata/t187ap03_L"
    logger.info(f"Fetching TWSE company profile data from {url}")
    try:
        # 透過 verify=False 跳過 SSL 憑證驗證
        resp = requests.get(url, headers={"Accept": "application/json"}, verify=False)
        resp.raise_for_status()
        
        # 設定正確的編碼 (UTF-8)
        resp.encoding = 'utf-8'
        data = resp.json()
        logger.info(f"Received {len(data)} company profiles from TWSE.")
        return json.dumps(data, indent=2, ensure_ascii=False)
    except requests.exceptions.SSLError as e:
        logger.error(f"SSL error occurred: {e}")
        logger.info("Trying to disable SSL warnings...")
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        # 再次嘗試並關閉警告
        resp = requests.get(url, headers={"Accept": "application/json"}, verify=False)
        resp.raise_for_status()
        
        # 設定正確的編碼 (UTF-8)
        resp.encoding = 'utf-8'
        data = resp.json()
        logger.info(f"Received {len(data)} company profiles from TWSE after disabling SSL verification.")
        return json.dumps(data, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Failed to fetch company profiles: {e}")
        return json.dumps([], indent=2)

@mcp.prompt
def stock_trend_analysis_prompt(stock_symbol: str, period: str) -> PromptMessage:
    """Prompt for Taiwan stock trend analysis using TWSE OpenAPI endpoints."""
    return twse_stock_trend_prompt(stock_symbol, period)


if __name__ == "__main__":
    mcp.run()