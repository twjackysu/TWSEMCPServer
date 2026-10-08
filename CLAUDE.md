# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

TWStockMCPServer is a Model Context Protocol (MCP) server for Taiwan stock market data analysis. Built with FastMCP (Python) and `requests`. Data sources:
- **TWSE OpenAPI** (`openapi.twse.com.tw`) — 106 tools: 公司治理、ESG、財務比率、公告名單、權證、券商
- **TWSE Web API** (`twse.com.tw`) — 19 tools（不帶 date 即回最新交易日／本月；取代了同資料的 OpenAPI 僅最新版）: 歷史日K、月均價、融資融券（`/exchangeReport`）；估值（`/rwd/zh/afterTrading/BWIBBU_d` —— `/exchangeReport/BWIBBU_ALL` 會忽略 `date` 參數，只回最新交易日，不可用於歷史查詢）；三大法人買賣超日報、個股明細（`/rwd/zh/fund/T86`）；三大法人買賣金額、全市場收盤行情、市場成交量值、加權指數歷史、外資持股歷史（`/rwd/zh/...`，可查任意過去日期，與同名 openapi.twse.com.tw 端點僅回傳最近約12個交易日不同）；個股月/年成交彙總、鉅額交易明細（無伺服器端股票篩選，本地端過濾）、融券借券餘額/成交、除權除息計算結果（TWT49U）、當日沖銷交易（TWTB4U）、全部指數含類股指數（MI_INDEX type=IND）（`/rwd/zh/...`）（legacy JSON，非 Swagger）
- **MIS 即時報價** (`mis.twse.com.tw`) — 1 tool: 盤中多股即時報價
- **TPEx OpenAPI** (`tpex.org.tw/openapi`) — 6 tools: 上櫃日收盤（最新一日；`get_otc_daily` 帶 date 時改用網站 afterTrading/otc，該來源不含定價交易、無均價）、三大法人彙總、注意股、處置股、零股、櫃買指數
- **TAIFEX OpenAPI** (`openapi.taifex.com.tw`) — 6 tools: 選擇權分析（Delta/OI增減）、保證金、年月統計（這些沒有下載頁對應）
- **TPEx 網站** (`www.tpex.org.tw/www/zh-tw/...`) — 6 tools: 上櫃個股日K、三大法人明細、融資融券、本益比/殖利率/淨值比、外資持股排行、除權除息計算結果（預設最新交易日，可查任意過去日期）
- **MOPS 公開資訊觀測站** (`mops.twse.com.tw/mops/api`, `mopsov.twse.com.tw`): 綜合損益表／資產負債表／現金流量表、月營收、股利（預設最新一期，可查任意過去期間；上市櫃、興櫃、公發公司皆可）、重大訊息（t05st01/t05st02 + 全文 *_detail）、董監持股與設質（stapap1）、內部人持股異動（query6_1）、庫藏股（t35sc09）、背書保證與資金貸與（t05st11）、法說會 — 11 tools
- **TDCC 集保** (`opendata.tdcc.com.tw`、`www.tdcc.com.tw/portal/zh/smWeb/qryStock`) — 1 tool: 集保戶股權分散表（`weeks=1` 最新一週完整級距，走開放資料 CSV；`weeks` 2–13 為逐週大戶／散戶趨勢，走查詢頁）
- **國發會** (`ws.ndc.gov.tw`，data.gov.tw 6099/6100) — 2 tools: 景氣對策信號與景氣指標、PMI/NMI
- **中央銀行** (`cpx.cbc.gov.tw`) — 1 tool: 每日匯率
- **衍生分析** (`tools/analytics/`) — 4 tools: 還原權息日K、技術指標、選股 screener、同業比較（`utils/market_snapshot.py`：估值與行情取同一資料日；上市/上櫃產業代碼同一套）。由 `utils/price_series.py`（上市 STOCK_DAY／上櫃 tradingStock 日K、TWT49U／exDailyQ 除權息，自動判斷市場並還原）與 `utils/indicators.py`（純計算）組成
- **TAIFEX 網站下載** (`www.taifex.com.tw/cht/3/*Down`) — 10 tools: 期貨／選擇權每日行情、三大法人（期貨/選擇權分計、總表、各期貨契約、各選擇權契約、買賣權分計）、期貨與選擇權大額交易人（無伺服器端契約篩選，本地端過濾）、Put/Call Ratio。日期留空＝最新交易日（往回逐日找有資料的一天），也可查過去區間。2026-09-29 逐列比對：最新一日的資料涵蓋同名 openapi 端點的全部內容且更完整，因此取代了那 9 個 openapi 工具；選擇權大額交易人於 2026-10-07 同樣逐列比對（320 列，僅「所有月份總計」代碼 999912 vs 999999 不同）後也改用下載頁（largeTraderOptDown，一次最多約一個月，整年區間會被拒絕）

## Development Commands

| Task | Command |
|------|---------|
| Install dependencies | `uv sync` |
| Install with test deps | `uv sync --extra dev` |
| Run server (dev) | `uv run fastmcp dev server.py` |
| Run server (prod) | `uv run fastmcp run server.py` |
| Run all tests | `uv run pytest` |
| Run specific test file | `uv run pytest tests/e2e/test_history_api.py -v` |
| Run tests by category | `python run_tests.py history` (also: `realtime`, `otc`, `taifex`, `institutional`, `mops`, `macro`, `e2e`) |
| Quick test (fail fast) | `python run_tests.py quick` |
| Tests with coverage | `python run_tests.py cov` (opens HTML report) |
| Run server directly | `python server.py` (HTTP on port 8000) |

## Code Architecture

### High-Level Structure

```
server.py                     # Thin entrypoint: FastMCP init, prompt registration, tool registration
utils/
├── api_client.py             # TWSEAPIClient - all TWSE HTTP calls
├── mops.py                   # MOPS helpers: mops_post (JSON API), mops_legacy_post (HTML), titles/HTML-table parsing
├── taifex.py                 # TAIFEX helpers: headers, cp950 CSV decode, date ranges, latest-trading-day lookup (fetch_period)
├── price_series.py           # Daily bars (listed/OTC auto-detected) + ex-rights events + backward adjustment
├── indicators.py             # Pure functions: SMA/EMA/RSI/KD/MACD/Bollinger
├── market_snapshot.py        # Latest-day listed+OTC valuation/price snapshot (same data date) and industry membership
├── config.py                 # APIConfig, DisplayConfig, TestConfig (env var overrides)
├── constants.py              # Localized message templates (Chinese)
├── date_helper.py            # roc_to_ad() / ad_to_roc() for TWSE legacy ROC dates; taipei_today()
├── decorators.py             # @handle_api_errors
├── formatters.py             # Data → string formatting functions
├── tool_factory.py           # create_company_tool() for dynamically named tools
└── types.py                  # TWSEDataItem TypedDict, DataFormatter Protocol
tools/
├── __init__.py               # register_all_tools() - auto-discovers and registers all tool modules
├── broker.py                 # Broker data tools (top-level module)
├── other.py                  # Misc tools: funds, bonds, holidays (top-level module)
├── company/                  # Company tools: basic_info, financials, esg, listing, news
├── trading/                  # Trading tools: dividend_schedule, etf, market, warrants
├── market/                   # Market tools: indices, statistics, foreign
├── history/                  # TWSE legacy: stock_day, stock_day_avg, margin_balance (exchangeReport); bwibbu_all (rwd/*);
                              #   institutional (T86);
                              #   institutional_amounts, all_stocks_daily_close, market_turnover, taiex_index_history,
                              #   foreign_holdings_history, stock_monthly_yearly_history, block_trades_detail,
                              #   short_sale_lending, exright_day_trading_indices (rwd/* endpoints — accept arbitrary past dates, unlike the
                              #   openapi.twse.com.tw equivalents which only return a rolling ~12-day window)
├── mops/                     # MOPS: financial_statements, monthly_revenue, dividend, investor_conference,
                              #   major_news, insiders, treasury_guarantees
├── tdcc/                     # TDCC: shareholding_distribution (open data CSV + query page)
├── macro/                    # ndc_indicators (景氣燈號, PMI), exchange_rates (央行)
├── analytics/                # price_tools (adjusted prices, technical indicators), screening (stock screener, industry peers)
├── realtime/                 # MIS real-time quotes: stock_info
├── otc/                      # TPEx OTC market: daily_close, institutional_summary,
                              #   odd_lot, index, trading_halt (注意股/處置股) (openapi, latest day); exright (website bulletin/exDailyQ);
                              #   history, valuation_holdings (www.tpex.org.tw website JSON: stock OHLC, 三大法人, 融資融券,
                              #   本益比, 外資持股; latest or any past date)
└── taifex/                   # TAIFEX derivatives. Download pages (latest day or any period):
                              #   daily_market_report, futures_position, institutional_details,
                              #   institutional_general, large_traders_oi (futures + options), put_call_ratio.
                              #   openapi.taifex.com.tw (latest day only, no download-page counterpart):
                              #   options_analytics, margin, trading_statistics.
                              #   Shared helpers (headers, CSV decode, date range, latest-day lookup) live
                              #   in utils/taifex.py
prompts/                      # 9 prompt templates registered in server.py
```

### Key Architectural Patterns

**Dependency Injection**: `server.py` creates one `TWSEAPIClient` instance and passes it to `register_all_tools(mcp, api_client)`. The auto-discovery engine in `tools/__init__.py` uses `pkgutil.iter_modules` to find all tool modules, then calls `module.register_tools(mcp, client)` on each.

**Tool Module Contract**: Every tool module must expose:
```python
def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
```
The `client` is captured via closure. Tools are registered with `@mcp.tool` — the function docstring becomes the MCP tool description.

**Auto-Discovery**: `tools/__init__.py` scans direct modules (`tools/broker.py`, `tools/other.py`) and subpackage modules (`tools/company/*.py`, etc.) automatically. No manual registration needed in `server.py` when adding new tool modules.

**API Client**: `TWSEAPIClient` has instance methods (`fetch_data`, `fetch_company_data`, `fetch_latest_market_data`) and class-method wrappers (`get_data`, `get_company_data`, `get_latest_market_data`) for backward compatibility. Instance methods are preferred. Includes built-in rate limiting (0.5s between requests). For non-OpenAPI sources (legacy TWSE, MIS, TPEx, TAIFEX), use `fetch_json(url, params)` / `get_json(url, params)` which accepts full URLs with query parameters and returns raw JSON (pass `json_body=` to send a JSON POST instead of a GET), and `fetch_bytes(url, data=, method=)` for CSV/zip/HTML bodies.

**Decorators**: Tool functions use decorators from `utils/decorators.py`:
- `@handle_api_errors(use_code_param=True)` — wraps in try/except, returns localized error message via `MSG_QUERY_FAILED`

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
- `TWSE_CACHE_TTL` (default: `60` seconds — in-memory cache for `fetch_data` OpenAPI list responses; `0` disables every cache, including the one below)
- `TWSE_RESPONSE_CACHE_MAX_ENTRIES` (default: `256`) — bound on the per-call response cache that `fetch_json` / `fetch_bytes` use when a tool passes `cache_ttl=` (TAIFEX download pages 300s, MOPS 600s, TDCC/CBC 1h, NDC 6h). It stores raw bytes, so callers can't mutate each other's data; only successful responses are cached
- `DISPLAY_LIMIT` (default: `50`)
- `PYTEST_DELAY_SECONDS` (default: `1.0` — rate limit delay between tests)

## Testing

Two kinds of tests, kept strictly apart:

- **Live contract tests** (`tests/test_api_schemas.py`, `tests/e2e/`) call the real third-party APIs. Their only job is to detect an interface change on TWSE / TAIFEX / TPEx / MIS that would break our tools: endpoint gone, response format changed (JSON → CSV/HTML, list → dict), a field or column our tool hardcodes renamed/moved. They must **not** assert on our own logic (pagination, output caps, filtering, message wording), and must **not** assert that upstream has data today — an empty `[]` from a "latest day only" endpoint is not an interface change (TWSE `t187ap42_L` served `[]` for days after the 2026 Mid-Autumn long weekend). Use `records_or_skip()` from `tests/helpers.py` for such endpoints. Fixed historical dates (`FIXED_DATE`) are expected to have data, so an empty result there is still a failure.
- **Offline unit tests** (every `tests/test_*.py` except `test_api_schemas.py`; most are named `*_unit.py`) test our own logic against canned payloads — via `OfflineClient` (`tests/offline.py`, stubs only the HTTP layer so client-side filtering still runs) or a small stub client. Mark the module `pytestmark = pytest.mark.offline`: `conftest.py` then skips the rate-limit sleep and makes any real HTTP request fail the test.

The `conftest.py` autouse fixture sleeps between live tests to avoid rate limiting.

**Test files**:
- `tests/test_api_schemas.py` — parametrized tests that verify fields tools **hardcode with `.get()`** still exist in live API responses. Endpoints are defined in `tests/tool_field_dependencies.py`. Only catches breakage that would silently return "N/A" in a tool.
- `tests/tool_field_dependencies.py` — the source of truth: maps each TWSE OpenAPI endpoint to the list of field names its tool hardcodes. Edit this file when adding or changing hardcoded field access in a tool.
- `tests/e2e/test_*.py` — per-category E2E tests (history, realtime, otc, taifex, institutional, mops, otc_history, tdcc_macro). For non-TWSE-OpenAPI tools (TAIFEX, OTC, MIS, legacy exchangeReport, MOPS, TDCC, NDC, CBC), field assertions live here instead. Use `fetch_bytes_or_skip()` from `tests/helpers.py` for CSV/zip/HTML sources.
- `tests/test_output_limits_unit.py`, `tests/test_summary_row_filtering_unit.py` — offline guards for pagination/output caps and summary-row and placeholder filtering.
- `tests/test_prompt_tool_references_unit.py` — every `get_xxx(` named in `prompts/` must be a registered tool; update the prompts when removing or renaming a tool.

**Fixtures** in `conftest.py`: `sample_stock_code` returns `"2330"` (TSMC), `sample_stock_code_with_data` returns `"1210"`.

**CI**: GitHub Actions runs daily at 9:00 AM Taiwan time. On failure, auto-creates an issue labeled `api-change,bug,automated`; auto-closes when tests pass again.

## Adding New Tools

1. Check for overlap first. Don't ship two tools for the same data. Decide overlap from the upstream data, never from tool names or descriptions: fetch both endpoints for the same day and compare row sets, columns and values. If a new source covers an existing tool's data with more range (history, more markets, more columns), make the new tool's period parameters optional so it also serves the "latest" case, give it the existing tool's name, and delete the old one (plus its field dependencies/tests, and update `prompts/`). Tools covering different scopes (e.g. whole-market latest snapshot vs. one stock's month of history) are not overlaps.
2. Add tool function in the appropriate module under `tools/` (or create a new module)
3. Ensure the module has `register_tools(mcp, client)` — it will be auto-discovered
4. Use `@mcp.tool` decorator; the docstring becomes the MCP tool description
5. Use `@handle_api_errors()` for standardized error handling; check for empty/None results explicitly and return `MSG_NO_DATA.format(data_type=...)`
6. Use `client.fetch_company_data(endpoint, code)` for company-specific lookups, `client.fetch_data(endpoint)` for general data
7. Format output with utilities from `utils/formatters.py`
8. **API field tests** — only required when the tool hardcodes field names with `.get("field")`:
   - **TWSE OpenAPI tools** (`fetch_data` / `fetch_company_data`): add the endpoint and its hardcoded fields to `tests/tool_field_dependencies.py`. The parametrized test in `tests/test_api_schemas.py` will pick it up automatically.
   - **Non-TWSE-OpenAPI tools** (TAIFEX, OTC/TPEx, MIS, legacy `exchangeReport`, MOPS, TDCC, NDC, CBC): add a `test_hardcoded_fields_exist` method to the relevant `tests/e2e/test_*.py` file.
   - **No hardcoded fields** (tool uses `format_properties_with_values_multiline` to dump all fields generically): no API field test needed — the tool adapts automatically to schema changes.

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

`staticFiles/apis_summary_simple.json` contains all available TWSE OpenAPI endpoints with their schemas.

### External API Notes

- **TWSE exchangeReport** (`tools/history/`): Legacy JSON endpoints returning `{"stat": "OK", "data": [...]}`. Dates in ROC format — use `utils/date_helper.py` for conversion. `MI_MARGN` uses `tables` array instead of `data`.
- **MIS** (`tools/realtime/`): Single-letter field names (`z`=price, `c`=code, `ex`=market type). Use `tse_` prefix for listed stocks, `otc_` for OTC; tool auto-retries with `otc_` if `tse_` returns no data.
- **TPEx** (`tools/otc/`): Standard REST JSON. Swagger spec at `tpex.org.tw/openapi/swagger.json`. Field names use English (e.g. `SecuritiesCompanyCode`).
- **TAIFEX** (`tools/taifex/`): Requires browser-like `User-Agent` header (the default `stock-mcp/1.0` gets HTML instead of JSON). `TAIFEX_HEADERS`, `decode_and_parse_csv` (cp950; an HTML page — including `<!DOCTYPE HTML` — means no data), `parse_date_range` and `fetch_period` (empty dates → walk back from today, Taiwan time, to the latest day with data; `is_complete` lets the market reports skip a day that only has the overnight 盤後 session so far) live in `utils/taifex.py`.
  - `openapi.taifex.com.tw` intermittently answers with an endpoint's **CSV** form (Chinese column headers) instead of JSON, even when the request sends `Accept: application/json`. The degradation is per-endpoint and lasts minutes, so `--reruns` does not clear it — measured 2026-08-28, `va01`/`PutCallRatio` served CSV for a stretch and JSON afterwards, while `MarketDataOfMajorInstitutionalTradersDividedByFuturesAndOptionsBytheDate` served CSV on 30/30 consecutive requests as its siblings served JSON. Tests treat this as transient and skip (`_is_taifex_csv_fallback` in `tests/helpers.py`); `test_openapi_still_serves_json_for_some_endpoint` fails if *every* probed endpoint goes CSV, which would mean a real site-wide format change. Tools currently surface these windows as `查詢失敗`.
- **MOPS** (`tools/mops/`, `utils/mops.py`): No public docs. To find a page: the main bundle `https://mops.twse.com.tw/mops/assets/index.js` lists every route as `{path:"/web/<pageId>", name:"<中文頁名>"}`. The SPA's form field names are in per-page JS chunks (`https://mops.twse.com.tw/mops/assets/<pageId>.js`, action `{apiName, type}`); how the body is assembled for a few pages (e.g. `query6_1` needs `subsidiaryCompanyId`) is in index.js — grep it for the page id. `type:"base"` → `POST /mops/api/<apiName>` JSON, reply `{"code", "message", "result"}` (`code` 406 = 查無資料, 500 = bad parameters); `type:"twse"` → legacy `POST mopsov.twse.com.tw/mops/web/<apiName>` form (plus hidden `encodeURIComponent/step/firstin/off` fields), HTML reply. Tables come as nested `titles` + rows; render via `flatten_titles` / `leaf_titles` rather than hardcoding line items (they differ by industry). Legacy `ajax_t100sb02_1` (法說會) only accepts zero-padded months (`09`, not `9`). Legacy pages often have tables without ids and start a new `<table>` every few hundred rows without closing the previous one (`ajax_t35sc09`); `parse_html_tables` handles both.
- **TPEx website** (`tools/otc/history.py`): `www.tpex.org.tw/www/zh-tw/...?response=json` with `date=YYYY/MM/DD`; rows are in `tables[0].data`. `insti/dailyTrade` repeats identical column names for 7 買進/賣出/買賣超 groups — the contract test checks the group order via their sums.
- **NDC** (`tools/macro/ndc_indicators.py`): `index.ndc.gov.tw` is behind a Cloudflare bot block — don't try to get around it. Use the fixed `ws.ndc.gov.tw/Download.ashx` links from data.gov.tw datasets 6099 (zip of CSVs) and 6100 (PMI CSV); if NDC re-points them the contract tests fail.
- **CBC** (`tools/macro/exchange_rates.py`): `cpx.cbc.gov.tw/API/DataAPI/Get?FileName=BP01D01`; the file is refreshed about monthly, so the latest weeks may be absent.
- **TDCC query page** (`tools/tdcc/shareholding_distribution.py`): `www.tdcc.com.tw/portal/zh/smWeb/qryStock` has no CAPTCHA, but it is a stateful form: GET the page (sets `JSESSIONID`; hidden `SYNCHRONIZER_TOKEN`, `firDate`, and a `scaDate` list of ~51 weeks newest first), then POST `SYNCHRONIZER_TOKEN`, `SYNCHRONIZER_URI=/portal/zh/smWeb/qryStock`, `method=submit`, `firDate`, `scaDate`, `sqlMethod=StockNo`, `stockNo`, `stockName`. Tokens are single-use and every reply carries the next one, so the tool chains them inside one `requests.Session` (`fetch_bytes(..., session=)`, which also bypasses the response cache) and reloads the page if a reply has none. Unknown code → `查無此資料`. Compared with the open-data CSV (2026-10-02; 2330, 6488, 0050): levels 1–15 and the total are identical; only 差異數調整 differs (page keeps the sign and drops the row when zero), so the trend ignores it. Past weeks are immutable and kept in an in-process cache.
