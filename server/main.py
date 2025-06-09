from fastapi import FastAPI, HTTPException

from .tools.twse import TWSETool

app = FastAPI(title="TW Stock MCP Server")

# Pre-defined tools mapping names to TWSE API endpoints
TOOLS = {
    "all_stocks": TWSETool("/v1/tradingInfo/allStocks"),
    "daily_summary": TWSETool("/v1/exchangeReport/STOCK_DAY_AVG_ALL"),
}

@app.get("/query/{tool_name}")
async def query(tool_name: str, params: dict | None = None):
    tool = TOOLS.get(tool_name)
    if not tool:
        raise HTTPException(status_code=404, detail="tool not found")
    return tool.query(params)
