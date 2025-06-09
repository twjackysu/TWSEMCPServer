from fastapi import HTTPException
from fastapi.responses import JSONResponse
from fastmcp import FastMCP

from .tools.twse import TWSETool

app = FastMCP(title="TW Stock MCP Server")

# Pre-defined tools mapping names to TWSE API endpoints
TOOLS = {
    "all_stocks": TWSETool("/v1/tradingInfo/allStocks"),
    "daily_summary": TWSETool("/v1/exchangeReport/STOCK_DAY_AVG_ALL"),
}


@app.get("/")
async def root():
    """Basic health check endpoint."""
    return {"status": "ok"}


@app.post("/initialize")
async def initialize():
    """Return basic server capabilities."""
    return JSONResponse({"tools": list(TOOLS.keys())})

@app.get("/query/{tool_name}")
async def query(tool_name: str, params: dict | None = None):
    import traceback
    tool = TOOLS.get(tool_name)
    if not tool:
        raise HTTPException(status_code=404, detail="tool not found")
    try:
        return tool.query(params)
    except Exception as e:
        print(f"Error in query: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
