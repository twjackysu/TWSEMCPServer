# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

TWStockMCPServer is a Model Context Protocol (MCP) server for Taiwan Stock Exchange (TWSE) data analysis. It provides comprehensive stock information, financial statements, ESG data, and trend analysis functionality through the TWSE OpenAPI.

## Development Commands

### Environment Setup
```bash
# Install dependencies using uv (recommended)
uv sync

# Alternative using pip
pip install -r requirements.txt
```

### Running the Server
```bash
# Development mode with hot reload
uv run fastmcp dev server.py

# Production mode
uv run fastmcp run server.py

# Direct execution
python server.py
```

### Dependencies
- **FastMCP**: Core MCP framework (>=2.7.1)
- **httpx**: Async HTTP client (>=0.28.1) 
- **mcp[cli]**: MCP CLI tools (>=1.9.3)
- **requests**: HTTP library for TWSE API calls (>=2.32.4)

## Code Architecture

### Core Components

**server.py**: Main MCP server implementation containing:
- 15+ MCP tools for TWSE data retrieval
- 1 MCP prompt for stock trend analysis
- Base URL: `https://openapi.twse.com.tw/v1`
- SSL verification disabled (`verify=False`) for TWSE API compatibility
- UTF-8 encoding handling for Traditional Chinese data

### Tool Categories

**Company Information**:
- `get_company_profile()` - Basic company info from `/opendata/t187ap03_L`
- `get_company_dividend()` - Dividend data from `/opendata/t187ap45_L`
- `get_company_monthly_revenue()` - Monthly revenue from `/opendata/t187ap05_L`

**Trading Data**:
- `get_stock_daily_trading()` - Daily trading from `/exchangeReport/STOCK_DAY_ALL`
- `get_stock_monthly_average()` - Monthly averages from `/exchangeReport/STOCK_DAY_AVG_ALL`
- `get_stock_valuation_ratios()` - P/E, dividend yield, P/B from `/exchangeReport/BWIBBU_ALL`
- `get_stock_monthly_trading()` - Monthly trading from `/exchangeReport/FMSRFK_ALL`
- `get_stock_yearly_trading()` - Yearly trading from `/exchangeReport/FMNPTK_ALL`

**Financial Statements**:
- `get_company_income_statement()` - Income statement from `/opendata/t187ap06_L_ci`
- `get_company_balance_sheet()` - Balance sheet from `/opendata/t187ap07_L_ci`

**Market Data**:
- `get_market_index_info()` - Market indices from `/exchangeReport/MI_INDEX`
- `get_margin_trading_info()` - Margin trading from `/exchangeReport/MI_MARGN`

**ESG & Governance**:
- `get_company_governance_info()` - Governance from `/opendata/t187ap46_L_9`
- `get_company_climate_management()` - Climate data from `/opendata/t187ap46_L_8`
- `get_company_risk_management()` - Risk management from `/opendata/t187ap46_L_19`
- `get_company_supply_chain_management()` - Supply chain from `/opendata/t187ap46_L_13`
- `get_company_info_security()` - Information security from `/opendata/t187ap46_L_16`

### Data Processing Pattern

All tools follow the same pattern:
1. Make HTTP request to TWSE API with `verify=False` and 30s timeout
2. Set UTF-8 encoding for proper Traditional Chinese handling
3. Filter data by company code (`公司代號` or `Code`)
4. Format using `format_properties_with_values_multiline()` helper
5. Return formatted string or empty string on error
6. Log operations using Python's logging module

### Prompt System

**prompts/twse_stock_trend_prompt.py**: Contains comprehensive prompt template for Taiwan stock trend analysis with:
- Multi-timeframe analysis (short/medium/long-term)
- Technical, fundamental, and chip analysis perspectives
- Specific API endpoint recommendations for each analysis type
- Structured output format with reasoning and conclusions

### Static Files

**staticFiles/apis_summary_simple.json**: Reference documentation of available TWSE API endpoints with schemas, used for identifying new tools to implement.

## Development Notes

- No testing framework detected - manual testing recommended
- Chinese language comments and data fields throughout codebase
- Error handling includes logging but returns empty strings on failure
- All API calls include proper User-Agent header: "stock-mcp/1.0"
- Rate limiting considerations apply due to TWSE API constraints
- SSL verification disabled specifically for TWSE API compatibility

## Adding New Tools

1. Reference `staticFiles/apis_summary_simple.json` for available TWSE endpoints
2. Follow existing tool pattern in `server.py`
3. Use `@mcp.tool` decorator
4. Include comprehensive docstring
5. Implement error handling and logging
6. Use `format_properties_with_values_multiline()` for consistent output formatting