# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

TWStockMCPServer is a Model Context Protocol (MCP) server for Taiwan Stock Exchange (TWSE) data analysis. It provides comprehensive stock information, financial statements, ESG data, and trend analysis functionality through the TWSE OpenAPI.

## Development Commands

### Quick Reference

| Task | Command |
|------|---------|
| Install dependencies | `uv sync` |
| Install with tests | `uv sync --extra dev` |
| Run server (dev) | `uv run fastmcp dev server.py` |
| Run server (prod) | `uv run fastmcp run server.py` |
| Run all tests | `uv run pytest` |
| Run tests with coverage | `python run_tests.py cov` |
| Run specific test | `uv run pytest tests/e2e/test_esg_api.py -v` |
| Quick test (fail fast) | `python run_tests.py quick` |

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

### Development Dependencies (Optional)
```bash
# Install test dependencies
uv sync --extra dev
```
- **pytest**: Testing framework (>=7.4.0)
- **pytest-cov**: Coverage reporting (>=4.1.0)
- **pytest-mock**: Mocking support (>=3.11.1)
- **pytest-asyncio**: Async test support (>=0.21.0)

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
  - `get_twse_events(top=10)` - TWSE events from `/news/eventList` (optional top parameter)

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
  - `get_market_index_info(category="major", count=20, format="detailed")` - Market indices with advanced filtering from `/exchangeReport/MI_INDEX`
    - **category**: Filter by index type (major, sector, esg, leverage, return, thematic, dividend, all)
    - **count**: Limit number of results (default: 20, max: 50 for specific categories)
    - **format**: Output format (detailed, summary, simple)
    - Uses pattern matching for automatic categorization (avoids hardcoded index names)
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

## Testing

### Test Location and Structure

The project uses **pytest** for E2E (End-to-End) testing of TWSE API integrations:

```
tests/
├── conftest.py              # Shared pytest fixtures
├── test_api_client.py       # API client tests
└── e2e/
    └── test_esg_api.py      # ESG API E2E tests
```

### Running Tests

#### Quick Test Commands
```bash
# Run all tests (recommended)
uv run pytest

# Run specific test file
uv run pytest tests/e2e/test_esg_api.py -v

# Run with coverage report
uv run pytest --cov=tools --cov=utils --cov-report=html

# Run and open HTML coverage report automatically
python run_tests.py cov
```

#### Using run_tests.py Script
```bash
python run_tests.py all      # All tests
python run_tests.py esg      # ESG API tests only
python run_tests.py api      # API client tests only
python run_tests.py cov      # With coverage + auto-open HTML report
python run_tests.py quick    # Stop at first failure
```

### Test Coverage

Current test coverage (see `API_TODO.md` for details):
- **7 APIs tested** (19.4% of implemented APIs)
- **100% coverage** of ESG APIs
- Tests marked with 🧪 in API_TODO.md

Tested APIs:
- ✅ Anti-competitive litigation (`/opendata/t187ap46_L_20`)
- ✅ Risk management (`/opendata/t187ap46_L_19`)
- ✅ Information security (`/opendata/t187ap46_L_16`)
- ✅ Supply chain management (`/opendata/t187ap46_L_13`)
- ✅ Functional committees (`/opendata/t187ap46_L_9`)
- ✅ Climate management (`/opendata/t187ap46_L_8`)
- ✅ Company basic info (`/opendata/t187ap03_L`)

### Adding Tests for New APIs

When implementing a new API tool, **always add corresponding E2E tests**:

#### 1. Choose the Right Test File
- **ESG APIs**: Add to `tests/e2e/test_esg_api.py`
- **Company APIs**: Add to `tests/e2e/test_company_api.py` (create if needed)
- **Trading APIs**: Add to `tests/e2e/test_trading_api.py` (create if needed)

#### 2. Test Template
```python
class TestYourNewAPI:
    """Description of API being tested."""
    
    ENDPOINT = "/opendata/your_endpoint"
    EXPECTED_FIELDS = [
        "欄位1",
        "欄位2",
        "欄位3",
    ]
    
    def test_api_endpoint_is_accessible(self):
        """測試 API 端點可訪問."""
        data = TWSEAPIClient.get_data(self.ENDPOINT)
        assert data is not None, "API 應該回傳資料"
        assert isinstance(data, list), "API 應該回傳 list"
        assert len(data) > 0, "API 應該回傳至少一筆資料"
    
    def test_response_schema_matches_expected(self):
        """測試回應 schema 符合預期."""
        data = TWSEAPIClient.get_data(self.ENDPOINT)
        first_item = data[0]
        
        for field in self.EXPECTED_FIELDS:
            assert field in first_item, f"欄位 '{field}' 應該存在於回應中"
    
    def test_get_company_data_by_code(self, sample_stock_code):
        """測試依公司代號查詢資料."""
        data = TWSEAPIClient.get_company_data(self.ENDPOINT, sample_stock_code)
        
        if data:
            assert data.get("公司代號") == sample_stock_code
```

#### 3. Update API_TODO.md
After adding tests, mark the API with 🧪:
```markdown
- [x] 🧪 Your API Name - `/opendata/your_endpoint`
```

### CI/CD Integration

Tests run automatically via **GitHub Actions**:

#### Automatic Triggers
- ✅ Push to `main` or `develop` branch
- ✅ Pull requests to `main`
- ✅ Daily at 9:00 AM Taiwan time (monitors API changes)

#### Manual Trigger
1. Go to **Actions** tab on GitHub
2. Select **"TWSE API E2E Tests"**
3. Click **"Run workflow"**
4. Choose test scope:
   - `all` - Run all tests
   - `esg` - ESG API tests only
   - `api_client` - API client tests only

#### Test Failure Alerts
When tests fail (especially scheduled runs):
- 🔔 Automatically creates GitHub issue
- 📋 Labels: `api-change`, `bug`, `automated`
- 📝 Includes failure details and logs
- ✅ Auto-closes when tests pass again

### Viewing Test Results

#### 1. Terminal Output
```bash
uv run pytest --cov=tools --cov=utils --cov-report=term
```
Shows coverage summary in terminal.

#### 2. HTML Coverage Report (Recommended)
```bash
python run_tests.py cov
```
Automatically opens `htmlcov/index.html` in browser showing:
- Line-by-line coverage
- Missing coverage highlights
- Per-file statistics

#### 3. GitHub Actions Logs
Check the "🧪 Run all tests" step in Actions for:
- Test results
- Coverage statistics
- Failure details

### Test Best Practices

When adding new API tools:

1. **✅ DO**: Add E2E tests that call real TWSE APIs
2. **✅ DO**: Test schema validation (field names and types)
3. **✅ DO**: Test data format validation (company codes, dates, numbers)
4. **✅ DO**: Test filtering/query logic with real data
5. **✅ DO**: Use parametrized tests for testing multiple similar endpoints
6. **✅ DO**: Mark API with 🧪 in API_TODO.md after adding tests

7. **❌ DON'T**: Mock API responses (these are E2E tests)
8. **❌ DON'T**: Assume field names won't change (that's what tests catch!)
9. **❌ DON'T**: Skip edge case testing (empty results, invalid codes, etc.)

### Example: Adding Tests for New ESG API

```python
# tests/e2e/test_esg_api.py

@pytest.mark.parametrize("endpoint,name", [
    ("/opendata/t187ap46_L_9", "功能性委員會"),
    ("/opendata/t187ap46_L_20", "反競爭行為法律訴訟"),  # Your new API
])
def test_esg_api_endpoints_accessible(self, endpoint, name):
    """測試所有 ESG API 端點可訪問."""
    data = TWSEAPIClient.get_data(endpoint)
    assert data is not None, f"{name} API 應該回傳資料"
    assert isinstance(data, list), f"{name} API 應該回傳 list"
```

For detailed testing documentation, see:
- 📖 `TESTING.md` - Complete testing guide
- 📖 `.github/ACTIONS_GUIDE.md` - GitHub Actions usage
- 📖 `.github/UV_INTEGRATION.md` - UV and dependency management

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