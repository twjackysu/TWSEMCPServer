"""Main MCP server for Taiwan Stock Exchange data analysis."""

from fastmcp import FastMCP
import logging

from prompts import register_all_prompts
from toolkit import ArgumentErrorsInChinese, response_limit
from tools import SOURCES, enabled_sources, register_all_tools, show_only_sources
from utils.api_client import TWSEAPIClient
from utils.config import ServerConfig

# Configure logging (similar to .NET ILogger)
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# The data sources this deployment serves (TWSE_INCLUDE_SOURCES / TWSE_EXCLUDE_SOURCES; default all).
SERVED_SOURCES = enabled_sources(ServerConfig.INCLUDE_SOURCES, ServerConfig.EXCLUDE_SOURCES)

# Sent once to every client at initialization (MCP `instructions`), so the date convention that holds
# for all tools is not repeated in 177 tool descriptions. Replies keep the sources' ROC (民國) dates.
SERVER_INSTRUCTIONS = f"""台灣證券市場資料：{'、'.join(name for tag, name in SOURCES.items() if tag in SERVED_SOURCES)}。

日期慣例：
- 工具的日期參數（date、start_date、end_date）一律是西元 YYYYMMDD，例如 20260930；月份參數（YYYYMM）也是西元。
- 回覆中的日期常沿用資料來源的民國紀年，民國年 + 1911 = 西元年：115/09/30、115年09月30日、1150930 都是 2026-09-30，115年09月 是 2026 年 9 月。
- 財報期別 115/2、115Q2 是 2026 年第 2 季；股利年度 114 是 2025 年。
- 拿回覆中的民國日期再查詢時，先換算成西元，例如 1150930 → 20260930。
- 少數參數是「年度」而不是日期（例如公開資訊觀測站財報、股利、重大訊息的 year），西元或民國皆可，以各參數說明為準。"""

# Initialize FastMCP server
mcp = FastMCP("TWSE Stock Trend Analysis 🚀", instructions=SERVER_INSTRUCTIONS)
# FastMCP rejects arguments outside a tool's schema (toolkit/params.py); say why in Chinese.
mcp.add_middleware(ArgumentErrorsInChinese())
# Last resort against a runaway reply (e.g. limit=100000 on 44,717 warrants): cut it past
# TWSE_MAX_RESPONSE_BYTES (0 = off) and say so. Tools still limit their own rows.
if ServerConfig.MAX_RESPONSE_BYTES:
    mcp.add_middleware(response_limit(ServerConfig.MAX_RESPONSE_BYTES))

# Initialize API Client
# This is the root of our Dependency Injection tree
api_client = TWSEAPIClient()

# Pass dependencies to tool registration
tool_tags = register_all_tools(mcp, api_client)
# Every prompts/ module's prompt, tagged with the sources of the tools it names.
register_all_prompts(mcp, tool_tags)
# Hide tools (and prompts) of the sources this deployment does not serve (FastMCP Visibility on tags).
show_only_sources(mcp, SERVED_SOURCES)

if __name__ == "__main__":
    import os
    port = int(os.getenv("PORT", "8000"))
    if os.getenv("MCP_STDIO", "").lower() in ("1", "true"):
        # docker run -i --rm -e MCP_STDIO=1 ...
        mcp.run(transport="stdio")
    else:
        mcp.run(transport="http", host="0.0.0.0", port=port)
