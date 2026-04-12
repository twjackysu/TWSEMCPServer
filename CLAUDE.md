# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

TWStockMCPServer is a Model Context Protocol (MCP) server for Taiwan stock market data analysis. Built with FastMCP (Python) and `requests`. Data sources:
- **TWSE OpenAPI** (`openapi.twse.com.tw`) — 143 tools: 公司治理、ESG、財報、交易、指數、券商
- **TWSE exchangeReport** (`twse.com.tw/exchangeReport`) — 4 tools: 歷史日K、月均價、估值、融資融券（legacy JSON，非 Swagger）
- **MIS 即時報價** (`mis.twse.com.tw`) — 1 tool: 盤中多股即時報價
- **TPEx OpenAPI** (`tpex.org.tw/openapi`) — 3 tools: 上櫃日收盤、三大法人、本益比
- **TAIFEX OpenAPI** (`openapi.taifex.com.tw`) — 2 tools: 三大法人期貨部位、Put/Call Ratio

## Development Commands

| Task | Command |
|------|---------|
| Install dependencies | `uv sync` |
| Install with test deps | `uv sync --extra dev` |
| Run server (dev) | `uv run fastmcp dev server.py` |
| Run server (prod) | `uv run fastmcp run server.py` |
| Run all tests | `uv run pytest` |
| Run specific test file | `uv run pytest tests/e2e/test_esg_api.py -v` |
| Run tests by category | `python run_tests.py esg` (also: `company`, `financials`, `trading`, `warrants`, `other`, `history`, `realtime`, `otc`, `taifex`, `api`, `e2e`) |
| Quick test (fail fast) | `python run_tests.py quick` |
| Tests with coverage | `python run_tests.py cov` (opens HTML report) |
| Run server directly | `python server.py` (HTTP on port 8000) |

## Code Architecture

### High-Level Structure

```
server.py                     # Thin entrypoint: FastMCP init, prompt registration, tool registration
models/                       # Pydantic-style data models (MarketInfo, BrokerInfo, RealTimeStats)
utils/
├── api_client.py             # TWSEAPIClient - all TWSE HTTP calls
├── config.py                 # APIConfig, DisplayConfig, TestConfig (env var overrides)
├── constants.py              # Localized message templates (Chinese)
├── decorators.py             # @handle_api_errors, @handle_empty_response
├── formatters.py             # Data → string formatting functions
├── tool_factory.py           # create_company_tool() for dynamically named tools
└── types.py                  # TWSEDataItem TypedDict, DataFormatter Protocol
tools/
├── __init__.py               # register_all_tools() - auto-discovers and registers all tool modules
├── broker.py                 # Broker data tools (top-level module)
├── other.py                  # Misc tools: funds, bonds, holidays (top-level module)
├── company/                  # Company tools: basic_info, financials, esg, listing, news
├── trading/                  # Trading tools: daily, periodic, valuation, dividend_schedule, etf, market, warrants
├── market/                   # Market tools: indices, statistics, foreign
├── history/                  # TWSE legacy exchangeReport: stock_day, stock_day_avg, bwibbu_all, margin_balance
├── realtime/                 # MIS real-time quotes: stock_info
├── otc/                      # TPEx OTC market: daily_close, institutional, peratio
└── taifex/                   # TAIFEX derivatives: futures_position, put_call_ratio
prompts/                      # 5 prompt templates registered in server.py
```

### Key Architectural Patterns

**Dependency Injection**: `server.py` creates one `TWSEAPIClient` instance and passes it to `register_all_tools(mcp, api_client)`. The auto-discovery engine in `tools/__init__.py` uses `pkgutil.iter_modules` to find all tool modules, then calls `module.register_tools(mcp, client)` on each.

**Tool Module Contract**: Every tool module must expose:
```python
def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
```
The `client` is captured via closure. Tools are registered with `@mcp.tool` — the function docstring becomes the MCP tool description.

**Auto-Discovery**: `tools/__init__.py` scans direct modules (`tools/broker.py`, `tools/other.py`) and subpackage modules (`tools/company/*.py`, etc.) automatically. No manual registration needed in `server.py` when adding new tool modules.

**API Client**: `TWSEAPIClient` has instance methods (`fetch_data`, `fetch_company_data`, `fetch_latest_market_data`) and class-method wrappers (`get_data`, `get_company_data`, `get_latest_market_data`) for backward compatibility. Instance methods are preferred. Includes built-in rate limiting (0.5s between requests). For non-OpenAPI sources (legacy TWSE, MIS, TPEx, TAIFEX), use `fetch_json(url, params)` / `get_json(url, params)` which accepts full URLs with query parameters and returns raw JSON.

**Decorators**: Tool functions use decorators from `utils/decorators.py`:
- `@handle_api_errors(data_type="...", use_code_param=True)` — wraps in try/except, returns localized error message
- `@handle_empty_response(data_type="...")` — returns localized "no data" message for None/empty results

**Formatters**: `utils/formatters.py` provides:
- `format_properties_with_values_multiline(data)` — single record dict → multiline string
- `format_multiple_records(records, separator)` — multiple records with separators
- `format_list_response(data, data_type, formatter, limit)` — paginated list with total count
- `create_simple_list_formatter(name_field, code_field, *extra)` — factory for list formatters

**Company Data Filtering**: `fetch_company_data()` filters by `公司代號`, `Code`, or `權證代號` field matching the `code` parameter.

### Configuration

All configuration in `utils/config.py` reads from environment variables with sensible defaults. See `.env.example` for the full list:
- `TWSE_API_BASE_URL` (default: `https://openapi.twse.com.tw/v1`)
- `TWSE_REQUEST_INTERVAL` (default: `0.5` seconds)
- `TWSE_API_TIMEOUT` (default: `30.0` seconds)
- `TWSE_VERIFY_SSL` (default: `false` — required for TWSE API compatibility)
- `DISPLAY_LIMIT` (default: `20`)
- `PYTEST_DELAY_SECONDS` (default: `1.0` — rate limit delay between tests)

## Testing

Tests are E2E — they call real TWSE APIs (no mocking). The `conftest.py` has an autouse fixture that sleeps between tests to avoid rate limiting.

**Test files**:
- `tests/test_api_schemas.py` — parametrized schema drift detection against TWSE Swagger spec (falls back to `staticFiles/swagger_decoded.json`)
- `tests/e2e/test_*.py` — per-category E2E tests (esg, company, financials, trading, warrants, other, history, realtime, otc, taifex)

**Fixtures** in `conftest.py`: `sample_stock_code` returns `"2330"` (TSMC), `sample_stock_code_with_data` returns `"1210"`.

**CI**: GitHub Actions runs daily at 9:00 AM Taiwan time. On failure, auto-creates an issue labeled `api-change,bug,automated`; auto-closes when tests pass again.

## Adding New Tools

1. Add tool function in the appropriate module under `tools/` (or create a new module)
2. Ensure the module has `register_tools(mcp, client)` — it will be auto-discovered
3. Use `@mcp.tool` decorator; the docstring becomes the MCP tool description
4. Use `@handle_api_errors()` and `@handle_empty_response()` decorators for standardized error handling
5. Use `client.fetch_company_data(endpoint, code)` for company-specific lookups, `client.fetch_data(endpoint)` for general data
6. Format output with utilities from `utils/formatters.py`
7. Add E2E tests in the appropriate `tests/e2e/test_*.py` file
8. Mark the API with a checkmark in `API_TODO.md`

Example:
```python
def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    _client = client or TWSEAPIClient.get_instance()

    @mcp.tool
    @handle_api_errors(use_code_param=True)
    def get_new_data(code: str) -> str:
        """Tool description shown to MCP clients."""
        data = _client.fetch_company_data("/opendata/your_endpoint", code)
        return format_properties_with_values_multiline(data) if data else ""
```

## API Reference

`staticFiles/apis_summary_simple.json` contains all available TWSE OpenAPI endpoints with their schemas. `API_TODO.md` tracks implementation and test status for all 143 TWSE OpenAPI endpoints.

### External API Notes

- **TWSE exchangeReport** (`tools/history/`): Legacy JSON endpoints returning `{"stat": "OK", "data": [...]}`. Dates in ROC format — use `utils/date_helper.py` for conversion. `MI_MARGN` uses `tables` array instead of `data`.
- **MIS** (`tools/realtime/`): Single-letter field names (`z`=price, `c`=code, `ex`=market type). Use `tse_` prefix for listed stocks, `otc_` for OTC; tool auto-retries with `otc_` if `tse_` returns no data.
- **TPEx** (`tools/otc/`): Standard REST JSON. Swagger spec at `tpex.org.tw/openapi/swagger.json`. Field names use English (e.g. `SecuritiesCompanyCode`).
- **TAIFEX** (`tools/taifex/`): Requires browser-like `User-Agent` header (the default `stock-mcp/1.0` gets HTML instead of JSON). Uses its own `_fetch_taifex()` helper instead of `TWSEAPIClient`.
