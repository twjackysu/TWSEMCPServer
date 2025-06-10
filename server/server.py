from fastmcp import FastMCP
import requests
from prompts.twse_stock_trend_prompt import twse_stock_trend_prompt
from fastmcp.prompts.prompt import PromptMessage

mcp = FastMCP("Demo 🚀")

@mcp.tool
def json_type(data) -> str:
    """Return 'array' if input is a list, 'object' if input is a dict."""
    if isinstance(data, list):
        return "array"
    elif isinstance(data, dict):
        return "object"
    else:
        return "unknown"

@mcp.tool
def json_array_filter(json_array: list, key: str, value) -> list:
    """Return items in the JSON array where item[key] == value."""
    if not isinstance(json_array, list):
        return []
    return [item for item in json_array if isinstance(item, dict) and item.get(key) == value]

@mcp.tool
def fetch_json(url: str) -> object:
    """Fetch JSON from a URL and return response.json()."""
    resp = requests.get(url)
    resp.raise_for_status()
    return resp.json()

@mcp.tool
def parse_swagger(swagger_url: str) -> list:
    """Fetch a swagger.json and return a list of available APIs with method, endpoint, input schema, and output schema."""
    resp = requests.get(swagger_url)
    resp.raise_for_status()
    swagger = resp.json()
    apis = []
    paths = swagger.get("paths", {})
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
    return apis

@mcp.prompt
def stock_trend_analysis_prompt(stock_symbol: str, period: str) -> PromptMessage:
    """Prompt for Taiwan stock trend analysis using TWSE OpenAPI endpoints."""
    return twse_stock_trend_prompt(stock_symbol, period)

if __name__ == "__main__":
    mcp.run()