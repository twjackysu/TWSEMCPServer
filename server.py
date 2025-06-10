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
    resp = requests.get(url, headers=headers)
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
def fetch_twse_company_profile() -> list:
    """Fetches the basic profile data for all listed companies from TWSE OpenAPI (t187ap03_L)."""
    url = "https://openapi.twse.com.tw/v1/opendata/t187ap03_L"
    logger.info(f"Fetching TWSE company profile data from {url}")
    resp = requests.get(url, headers={"Accept": "application/json"})
    resp.raise_for_status()
    data = resp.json()
    logger.info(f"Received {len(data)} company profiles from TWSE.")
    return data

@mcp.prompt
def stock_trend_analysis_prompt(stock_symbol: str, period: str) -> PromptMessage:
    """Prompt for Taiwan stock trend analysis using TWSE OpenAPI endpoints."""
    return twse_stock_trend_prompt(stock_symbol, period)


if __name__ == "__main__":
    mcp.run()