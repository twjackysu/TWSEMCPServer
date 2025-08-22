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

### Modular Structure

The project follows a clean modular architecture with clear separation of concerns:

```
TWStockMCPServer/
├── server.py                    # Main MCP server (29 lines)
├── utils/                       # Shared utilities
│   ├── api_client.py           # TWSE API client
│   └── formatters.py           # Data formatting utilities
├── tools/                      # MCP tools organized by category
│   ├── company/                # Company-related tools (8 tools)
│   ├── trading/                # Trading data tools (5 tools)
│   └── market/                 # Market data tools (4 tools)
└── prompts/                    # MCP prompts
```

### Core Components

**server.py**: Lightweight main server (54 lines):
- MCP server initialization and tool registration
- 5 MCP prompts for comprehensive stock analysis
- Clean separation from business logic

**utils/**: Shared utility modules:
- `TWSEAPIClient`: Unified API client for TWSE data retrieval
- `format_properties_with_values_multiline()`: Single record formatting
- `format_multiple_records()`: Multiple records formatting
- Base URL: `https://openapi.twse.com.tw/v1`
- SSL verification disabled for TWSE API compatibility
- UTF-8 encoding handling for Traditional Chinese data

### Tool Categories (29 tools total)

**tools/company/** - Company-related tools (13 tools):
- **basic_info.py**: 
  - `get_company_profile()` - Basic company info from `/opendata/t187ap03_L`
  - `get_company_dividend()` - Dividend data from `/opendata/t187ap45_L`
  - `get_company_monthly_revenue()` - Monthly revenue from `/opendata/t187ap05_L`
- **financials.py**:
  - `get_company_income_statement()` - Income statement from `/opendata/t187ap06_L_ci`
  - `get_company_balance_sheet()` - Balance sheet from `/opendata/t187ap07_L_ci`
- **esg.py**:
  - `get_company_governance_info()` - Governance from `/opendata/t187ap46_L_9`
  - `get_company_climate_management()` - Climate data from `/opendata/t187ap46_L_8`
  - `get_company_risk_management()` - Risk management from `/opendata/t187ap46_L_19`
  - `get_company_supply_chain_management()` - Supply chain from `/opendata/t187ap46_L_13`
  - `get_company_info_security()` - Information security from `/opendata/t187ap46_L_16`
- **news.py**:
  - `get_company_major_news()` - Company announcements from `/opendata/t187ap04_L`
  - `get_twse_news(start_date, end_date)` - TWSE official news from `/news/newsList` (with optional date filtering)
  - `get_twse_events()` - TWSE events from `/news/eventList`

**tools/trading/** - Trading data tools (10 tools):
- **daily.py**: `get_stock_daily_trading()` - Daily trading from `/exchangeReport/STOCK_DAY_ALL`
- **periodic.py**: 
  - `get_stock_monthly_average()` - Monthly averages from `/exchangeReport/STOCK_DAY_AVG_ALL`
  - `get_stock_monthly_trading()` - Monthly trading from `/exchangeReport/FMSRFK_ALL`
  - `get_stock_yearly_trading()` - Yearly trading from `/exchangeReport/FMNPTK_ALL`
- **valuation.py**: `get_stock_valuation_ratios()` - P/E, dividend yield, P/B from `/exchangeReport/BWIBBU_ALL`
- **dividend_schedule.py**: `get_dividend_rights_schedule()` - Ex-dividend/rights schedule from `/exchangeReport/TWT48U_ALL`
- **etf.py**: `get_etf_regular_investment_ranking()` - ETF regular investment ranking from `/ETFReport/ETFRank`
- **warrants.py**:
  - `get_warrant_basic_info()` - Warrant basic info from `/opendata/t187ap37_L`
  - `get_warrant_daily_trading()` - Warrant trading data from `/opendata/t187ap42_L`
  - `get_warrant_trader_count()` - Warrant trader count from `/opendata/t187ap43_L`

**tools/market/** - Market data tools (6 tools):
- **indices.py**:
  - `get_market_index_info()` - Market indices from `/exchangeReport/MI_INDEX`
  - `get_market_historical_index()` - Historical TAIEX data from `/indicesReport/MI_5MINS_HIST`
- **statistics.py**:
  - `get_margin_trading_info()` - Margin trading from `/exchangeReport/MI_MARGN`
  - `get_real_time_trading_stats()` - Real-time statistics from `/exchangeReport/MI_5MINS`
- **foreign.py**:
  - `get_foreign_investment_by_industry()` - Foreign investment by industry from `/fund/MI_QFIIS_cat`
  - `get_top_foreign_holdings()` - Top 20 foreign holdings from `/fund/MI_QFIIS_sort_20`

### Data Processing Pattern

**Unified API Client**: All tools use `TWSEAPIClient` class with these methods:
- `get_data(endpoint)`: Generic data fetching
- `get_company_data(endpoint, code)`: Company-specific data with filtering
- `get_latest_market_data(endpoint, count)`: Latest market records

**Common Processing Pattern**:
1. Tools call appropriate `TWSEAPIClient` method
2. API client handles HTTP request with `verify=False` and 30s timeout
3. UTF-8 encoding set for proper Traditional Chinese handling
4. Data filtered by company code (`公司代號` or `Code`) when applicable
5. Format using utility functions:
   - `format_properties_with_values_multiline()` for single records
   - `format_multiple_records()` for multiple records with separators
6. Return formatted string or empty string on error
7. All operations logged using Python's logging module

**Tool Registration**: Each module provides `register_tools(mcp)` function that registers all its tools with the MCP instance.

### Prompt System

**prompts/** - 5 comprehensive prompt templates:
- **twse_stock_trend_prompt.py**: Taiwan stock trend analysis with multi-timeframe analysis
- **foreign_investment_analysis_prompt.py**: Foreign investment analysis and monitoring
- **market_hotspot_monitoring_prompt.py**: Market hotspot and trend monitoring
- **dividend_investment_strategy_prompt.py**: Dividend investment strategy analysis
- **investment_screening_prompt.py**: Investment screening and selection criteria

Each prompt provides:
- Multi-perspective analysis (technical, fundamental, market sentiment)
- Specific API endpoint recommendations for each analysis type
- Structured output format with reasoning and conclusions

### Static Files

**staticFiles/apis_summary_simple.json**: Reference documentation of available TWSE API endpoints with schemas, used for identifying new tools to implement.

## Development Notes

- **Architecture**: Clean modular design with separation of concerns
- **Error Handling**: Standardized try-catch pattern returning empty strings on failure
- **Logging**: All operations logged using Python's logging module
- **Encoding**: UTF-8 encoding for Traditional Chinese data
- **API Client**: Unified `TWSEAPIClient` with proper User-Agent: "stock-mcp/1.0"
- **SSL**: Verification disabled specifically for TWSE API compatibility
- **Testing**: Manual testing recommended (no framework detected)

## Adding New Tools

### 1. Choose Appropriate Module
- **Company tools**: Add to `tools/company/` (basic_info.py, financials.py, esg.py, or news.py)
- **Trading tools**: Add to `tools/trading/` (daily.py, periodic.py, valuation.py, dividend_schedule.py, etf.py, or warrants.py)  
- **Market tools**: Add to `tools/market/` (indices.py, statistics.py, or foreign.py)
- **New category**: Create new subdirectory under `tools/`

### 2. Implementation Pattern
```python
# In appropriate tools module (e.g., tools/company/basic_info.py)
from utils import TWSEAPIClient, format_properties_with_values_multiline

def register_tools(mcp):
    @mcp.tool
    def your_new_tool(code: str) -> str:
        """Comprehensive docstring describing the tool."""
        try:
            data = TWSEAPIClient.get_company_data("/your/endpoint", code)
            return format_properties_with_values_multiline(data) if data else ""
        except Exception:
            return ""
```

### 3. API Reference
- Check `staticFiles/apis_summary_simple.json` for available TWSE endpoints
- Use appropriate `TWSEAPIClient` method:
  - `get_company_data()` for company-specific data
  - `get_data()` for general endpoints
  - `get_latest_market_data()` for recent market data

### 4. Tool Registration
Tools are automatically registered when server starts via `tools.register_all_tools(mcp)`. No manual registration needed in `server.py`.

## Modular Benefits

- **Maintainability**: Each tool in its logical location
- **Scalability**: Easy to add new tools without touching main server
- **Reusability**: Shared utilities eliminate code duplication
- **Clarity**: Clear organization by business domain
- **Testing**: Individual modules can be tested independently