# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

TWStockMCPServer is a Model Context Protocol (MCP) server for Taiwan stock market data analysis. Built with FastMCP (Python) and `requests`. Data sources:
- **TWSE OpenAPI** (`openapi.twse.com.tw`) — 105 tools: 公司治理、ESG、財務比率、公告名單、權證、券商
- **TWSE Web API** (`twse.com.tw`) — 19 tools（不帶 date 即回最新交易日／本月；取代了同資料的 OpenAPI 僅最新版）: 歷史日K、月均價、融資融券（`/exchangeReport`）；估值（`/rwd/zh/afterTrading/BWIBBU_d` —— `/exchangeReport/BWIBBU_ALL` 會忽略 `date` 參數，只回最新交易日，不可用於歷史查詢）；三大法人買賣超日報、個股明細（`/rwd/zh/fund/T86`）；三大法人買賣金額、全市場收盤行情、市場成交量值、加權指數歷史、外資持股歷史（`/rwd/zh/...`，可查任意過去日期，與同名 openapi.twse.com.tw 端點僅回傳最近約12個交易日不同）；個股月/年成交彙總、鉅額交易明細（無伺服器端股票篩選，本地端過濾）、融券借券餘額/成交、除權除息計算結果（TWT49U）、當日沖銷交易（TWTB4U）、全部指數含類股指數（MI_INDEX type=IND）（`/rwd/zh/...`）（legacy JSON，非 Swagger）
- **MIS** (`mis.twse.com.tw`) — 2 tools: 盤中多股即時報價；ETF 已發行單位數／預估淨值／折溢價（`stock/data/all_etf.txt`，`get_etf_daily_nav`）
- **TPEx OpenAPI** (`tpex.org.tw/openapi`) — 5 tools: 上櫃日收盤（最新一日；`get_otc_daily` 帶 date 時改用網站 afterTrading/otc（`sources/tpex/daily_quotes.py`），該來源不含定價交易、無均價）、注意股、處置股、零股、櫃買指數
- **TAIFEX OpenAPI** (`openapi.taifex.com.tw`) — 6 tools: 選擇權分析（Delta/OI增減）、保證金、年月統計（這些沒有下載頁對應）
- **TPEx 網站** (`www.tpex.org.tw/www/zh-tw/...`) — 7 tools: 上櫃個股日K、三大法人明細（`insti/dailyTrade`，可依外資／投信／自營商排行）、三大法人買賣金額彙總（`insti/summary` 日／週／月，2026-10-19 與 openapi `tpex_3insti_summary` 8 列逐列相同後取代之）、融資融券、本益比/殖利率/淨值比、外資持股排行、除權除息計算結果（預設最新交易日，可查任意過去日期）
- **MOPS 公開資訊觀測站** (`mops.twse.com.tw/mops/api`, `mopsov.twse.com.tw`): 綜合損益表／資產負債表／現金流量表、月營收、股利（預設最新一期，可查任意過去期間；上市櫃、興櫃、公發公司皆可）、重大訊息（t05st01/t05st02 + 全文 *_detail）、董監持股與設質（stapap1）、內部人持股異動（query6_1）、庫藏股（t35sc09）、背書保證與資金貸與（t05st11）、法說會 — 11 tools
- **TDCC 集保** (`opendata.tdcc.com.tw`、`www.tdcc.com.tw/portal/zh/smWeb/qryStock`) — 1 tool: 集保戶股權分散表（`weeks=1` 最新一週完整級距，走開放資料 CSV；`weeks` 2–13 為逐週大戶／散戶趨勢，走查詢頁）
- **投信投顧公會 ETF 專區** (`www.sitca.org.tw/ROC/SITCA_ETF/`、`/ROC/Industry/IN2629|IN2630`，`utils/sitca.py`) — 3 tools: `get_etf_info`（所有投信、上市與上櫃 ETF 基本資料；單檔另合併證交所 t187ap47_L 與櫃買 ETF/detail，清單補上 SITCA 沒有的期信／外幣級別代號；取代了 `get_fund_basic_info`）、`get_etf_monthly_stats`（每月規模／淨值／受益人數／申購買回／定期定額，2007 起）、`get_etf_holdings`（成分股：基金投資明細每月前十大 2021-08 起、每季占淨值 1% 以上 2021-09 起；以基金名稱對回 ETF 代號，只做精確比對）
- **國發會** (`ws.ndc.gov.tw`，data.gov.tw 6099/6100) — 2 tools: 景氣對策信號與景氣指標、PMI/NMI
- **中央銀行** (`cpx.cbc.gov.tw`) — 1 tool: 每日匯率
- **衍生分析** (`tools/analytics/`) — 4 tools: 還原權息日K、技術指標、選股 screener、同業比較（`services/market_snapshot.py`：估值與行情取同一資料日；上市/上櫃產業代碼同一套）。由 `services/price_series.py`（上市 STOCK_DAY（`sources/twse/stock_day.py`）／上櫃 tradingStock（`sources/tpex/trading_stock.py`）日K、TWT49U（`sources/twse/twt49u.py`）／exDailyQ（`sources/tpex/ex_daily_q.py`）除權息，自動判斷市場並還原）與 `utils/indicators.py`（純計算）組成
- **TAIFEX 網站下載** (`www.taifex.com.tw/cht/3/*Down`、`dlFutPrevious30DaysSalesData`) — 11 tools: 期貨／選擇權每日行情、三大法人（期貨/選擇權分計、總表、各期貨契約、各選擇權契約、買賣權分計）、期貨與選擇權大額交易人（無伺服器端契約篩選，本地端過濾）、Put/Call Ratio。日期留空＝最新交易日（往回逐日找有資料的一天），也可查過去區間。2026-09-29 逐列比對：最新一日的資料涵蓋同名 openapi 端點的全部內容且更完整，因此取代了那 9 個 openapi 工具；選擇權大額交易人於 2026-10-07 同樣逐列比對（320 列，僅「所有月份總計」代碼 999912 vs 999999 不同）後也改用下載頁（largeTraderOptDown，一次最多約一個月，整年區間會被拒絕）。`get_futures_intraday`：最近 30 個交易日的每筆成交 zip 彙總成分鐘 K 線。`get_daily_futures_market_report` 的 contract 可填股票代號（openapi `SSFLists` 換成股票期貨契約）；`get_monthly_trading_statistics(market=)` 涵蓋期貨與選擇權（openapi）

## Development Commands

| Task | Command |
|------|---------|
| Install dependencies | `uv sync` |
| Install with test deps | `uv sync --extra dev` |
| Run server (dev) | `uv run fastmcp dev inspector server.py` |
| Run server (prod) | `uv run fastmcp run server.py` |
| Lint (CI gate) | `uv run ruff check .` — rules and pinned version in `pyproject.toml`: F, E4/E7/E9, B (bugs, not style) |
| Type check (CI gate) | `uv run pyright` — basic mode over the server's packages (not `tests/`); settings and pinned version in `pyproject.toml` |
| Run all tests | `uv run pytest` |
| Run specific test file | `uv run pytest tests/contract/test_history_api.py -v` |
| Run tests by category | `python run_tests.py history` (also: `realtime`, `otc`, `taifex`, `institutional`, `mops`, `macro`, `etf`; `contract` = all contract tests, `unit` = all offline unit tests) |
| Quick test (fail fast) | `python run_tests.py quick` |
| Tests with coverage | `python run_tests.py cov` (opens HTML report) |
| Run server directly | `python server.py` (HTTP on port 8000, `GET /health` → `ok`; `MCP_STDIO=1` for stdio) |
| Build Docker image | `docker build -t twse-mcp .` — two stages: uv (pinned) installs `uv.lock` without dev extras into `/app/.venv`; the runtime image holds that venv and the packages only (no uv, no Node.js), runs as user `app` (uid 10001), and its HEALTHCHECK GETs `/health` (healthy by default under stdio) |

Dependencies live in `pyproject.toml` + `uv.lock` only (no `requirements*.txt`); Prefect Horizon, which hosts the public server, reads `pyproject.toml`. Declare a package there only if our code imports it.

## Code Architecture

Refactoring roadmap: `docs/improvement-plan.md` (phases, progress, and a FastMCP 4 mapping). The server runs on FastMCP 4: reach for its own mechanisms first (`@mcp.tool` `annotations` / `tags` / `output_schema`, middleware, transforms such as `Visibility`) before writing an equivalent ourselves. Not `timeout=`: on a sync tool FastMCP cannot cancel the worker thread, so the client waits for the tool to finish anyway and then gets an error instead of the result (measured on 4.1.3) — limit time with `utils.deadline.time_budget` instead.

### High-Level Structure

```
server.py                     # Thin entrypoint: FastMCP init, tool then prompt registration, source filter
toolkit/                      # MCP-side building blocks for tool modules (only depends on utils/)
├── decorators.py             # @handle_api_errors — the tool error boundary (exception → ToolError)
├── factory.py                # CompanyToolSpec / ListToolSpec + create_company_tool / create_list_tool
├── params.py                 # Limit / Offset / TradingDate / RequiredTradingDate: parameter types FastMCP validates
├── validation.py             # ArgumentErrorsInChinese: middleware rewording FastMCP's argument-validation errors
├── response_limit.py         # response_limit(max_size, tools): FastMCP's ResponseLimitingMiddleware with the Chinese truncation notice
└── structured.py             # output_schema(Result) / structured_reply(text, result): text + dataclass replies (see Structured output)
services/                     # Data the tools need, assembled from gateways + pure logic (uses sources/, utils/)
├── price_series.py           # Daily bars (listed/OTC auto-detected) + ex-rights events + backward adjustment
└── market_snapshot.py        # Latest-day listed+OTC valuation/price snapshot (same data date, per market) and industry membership
sources/                      # Gateways: one module per upstream endpoint, typed records out (uses utils/ only)
├── columns.py                # column_index(): find columns by published field name, raise if one is gone; qualified_fields(): "group/name" from TWSE groups
├── caching.py                # month_cache_ttl() / year_cache_ttl() (past 1h / current 2 min), day_cache_ttl() (past days 1h / latest 10 min)
├── twse/stock_day.py         # STOCK_DAY → StockDayMonth / StockDayRow
├── twse/stock_day_avg.py     # STOCK_DAY_AVG → monthly_closes() MonthlyCloses (月平均收盤價 row printed without separators)
├── twse/mi_margn.py          # MI_MARGN → margin_balances() MarginDay (信用交易統計 + per-stock 融資/融券 by group/name; 註記 kept padded)
├── twse/fmsrfk.py            # FMSRFK → monthly_trading() MonthlyTradingYear (one stock, one year by month)
├── twse/fmnptk.py            # FMNPTK → yearly_trading() YearlyTrading list (each 日期 named after the price before it)
├── twse/fmtqik.py            # FMTQIK → market_turnover() MarketMonth (daily turnover + TAIEX close, one month)
├── twse/mi_5mins_hist.py     # MI_5MINS_HIST → taiex_history() IndexMonth (TAIEX daily OHLC, one month)
├── twse/bfi82u.py            # BFI82U → institutional_amounts() AmountReport (day / week / month; week needs its first trading day)
├── twse/mi_index.py          # MI_INDEX → stock_quotes() QuoteTable (ALLBUT0999 / industry code), index_quotes() IndexBoard (IND)
├── twse/twt49u.py            # TWT49U → exright_results() ExRightReport (stat kept for TWSE's own "nothing found" reason)
├── twse/bwibbu_d.py          # BWIBBU_d → valuation_ratios() ValuationReport (served date: a bad `date` gets the latest day)
├── institutional.py          # InstitutionalFlow / Trades / FlowDay (per stock) and InstitutionalAmount (market totals): the 三大法人 records both markets' gateways return
├── twse/t86.py               # T86 → t86_flows() (all three historical column layouts, by name)
├── twse/twt93u.py            # TWT93U → short_sale_lending_balances() (columns by group/name; 借券賣出 layout until 2012-03-16 kept as published)
├── twse/twtasu.py            # TWTASU → short_lending_sales() ShortLendingSaleDay (columns by group/name; 代號 and 名稱 split from one cell; 合計 left out)
├── twse/bfiauu.py            # BFIAUU → block_trades() BlockTradeDay (交割期別 until 2011-12-16; 總計 row left out)
├── twse/twtb4u.py            # TWTB4U → day_trading() DayTradingReport (tables found by fields; list only before the evening publication)
├── twse/mi_qfiis.py          # MI_QFIIS → foreign_holdings() ForeignHoldingDay (外資 names until 2009-04-30, 外資及陸資 after; ratios are JSON numbers)
├── tpex/insti_daily.py       # insti/dailyTrade → tpex_flows() (Adapter: groups by order, checked by their sums)
├── tpex/insti_summary.py     # insti/summary → otc_institutional_amounts() InstitutionalSummary (Daily/Weekly/Monthly; empty rows skipped)
├── tpex/trading_stock.py     # afterTrading/tradingStock → TradingStockMonth / TradingStockRow (volume column 成交張數, before 2025-01 成交仟股)
├── tpex/ex_daily_q.py        # bulletin/exDailyQ → otc_exright_results() OtcExRightReport (a range starting before 2016 has one more column)
├── tpex/daily_quotes.py      # afterTrading/otc → otc_daily_quotes() OtcQuoteDay (EW / AL / industry code; 最後買量・賣量 only from 2020-04-30)
├── tpex/pe_qry_date.py       # afterTrading/peQryDate → otc_valuation_ratios() OtcValuationReport (財報年/季 only from 2025-01-02)
├── tpex/margin_balance.py    # margin/balance → otc_margin_balances() OtcMarginDay (per-stock 融資/融券 + summary totals)
├── tpex/qfii.py              # insti/qfii → otc_foreign_holdings() OtcForeignHoldingDay (ratios published with %, rank order kept)
├── taifex/download.py        # download_table(): POST a download page's form, decode the cp950 CSV, columns by header name; number() / count()
├── taifex/daily_report.py    # futDataDown / optDataDown → futures_quotes() / option_quotes(); has_regular_session() for the latest-day walk-back
├── taifex/institutional.py   # 三大法人 pages → institutional_totals() / institutional_split() / *_contract_positions() / calls_puts_positions(): Positions (12 figures)
├── taifex/large_traders.py   # largeTraderFutDown / largeTraderOptDown → futures_large_traders() / option_large_traders() LargeTraderPosition
├── taifex/put_call_ratio.py  # pcRatioDown → put_call_ratios() PutCallRatioDay
├── mops/t35sc09.py           # legacy ajax_t35sc09 HTML → treasury_buybacks() Buyback (two-row header joined: 買回價格區間/最低)
├── mops/major_news.py        # t05st01 / t05st02 / *_detail → company_news(), market_news(), news_detail(): Announcement + NewsLink, by titles
└── mops/insiders.py          # stapap1 / query6_1 → board_holdings() (published columns kept), insider_changes() (本月增加/減少 by group title)
utils/                        # Bottom layer: HTTP, parsing, formatting. Never imports fastmcp / toolkit / tools / sources / services
├── api_client.py             # TWSEAPIClient - all TWSE HTTP calls
├── sitca.py                  # SITCA: ETF zone (month lists, result grid by code / 基金統編); 基金投資明細 (period postback, query by class, fund-name key)
├── mops.py                   # MOPS helpers: mops_post (JSON API), mops_legacy_post (HTML), titles/HTML-table parsing
├── taifex.py                 # TAIFEX helpers: headers, cp950 CSV decode, date ranges, latest-trading-day lookup (fetch_period)
├── indicators.py             # Pure functions: SMA/EMA/RSI/KD/MACD/Bollinger
├── config.py                 # APIConfig, DisplayConfig, TestConfig (env var overrides)
├── constants.py              # Localized message templates (Chinese)
├── date_helper.py            # roc_date() / roc_year_of() / slash_date(): a YYYYMMDD input → an upstream's form; parse_roc_date() / roc_to_ad() / roc_day() for ROC dates in replies; taipei_today()
├── errors.py                 # InvalidArgument (→ ToolError as is), UpstreamFormatError (a reply's shape changed)
├── parse.py                  # decimal_or_none() / int_or_none() / float_or_none(): every exchange-printed number in the repo; "--" → None (write `or 0` where none counts as 0)
├── pagination.py             # Page / Paged: limit/offset paging
├── formatters.py             # Data → string formatting functions; printed(): a gateway number as the exchange prints it; plain(): the same without separators (TAIFEX)
├── http_transport.py         # Per-site pooled sessions, TLS policy, UpstreamRetry
├── circuit_breaker.py        # Per-site circuit breaker: what counts as a failure / refusal, cooldown state
├── deadline.py               # time_budget(seconds, hint): a time limit shared by the upstream requests inside it
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
├── etf/                      # info (SITCA + t187ap47_L + TPEx ETF/detail), daily_nav (MIS all_etf.txt), monthly_stats, holdings (SITCA)
├── macro/                    # ndc_indicators (景氣燈號, PMI), exchange_rates (央行)
├── analytics/                # price_tools (adjusted prices, technical indicators), screening (stock screener, industry peers)
├── realtime/                 # MIS real-time quotes: stock_info
├── otc/                      # TPEx OTC market: daily_close, institutional_summary,
                              #   odd_lot, index, trading_halt (注意股/處置股) (openapi, latest day); exright (website bulletin/exDailyQ);
                              #   history, valuation_holdings (www.tpex.org.tw website JSON: stock OHLC, 三大法人, 融資融券,
                              #   本益比, 外資持股; latest or any past date)
└── taifex/                   # TAIFEX derivatives. Download pages (latest day or any period):
                              #   daily_market_report, futures_position, institutional_details,
                              #   institutional_general, large_traders_oi (futures + options), put_call_ratio,
                              #   intraday (tick-data zips → minute bars).
                              #   openapi.taifex.com.tw (latest day only, no download-page counterpart):
                              #   options_analytics, margin, trading_statistics.
                              #   Shared helpers (headers, CSV decode, date range, latest-day lookup) live
                              #   in utils/taifex.py
prompts/                      # 9 prompt templates, one per module, auto-discovered (prompts/__init__.py: register_all_prompts)
```

### Key Architectural Patterns

**Dependency Injection**: `server.py` creates one `TWSEAPIClient` instance and passes it to `register_all_tools(mcp, api_client)`. The auto-discovery engine in `tools/__init__.py` uses `pkgutil.iter_modules` to find all tool modules, then calls `module.register_tools(mcp, client)` on each. It fails fast: a module that cannot be imported or registered stops the server from starting instead of leaving it silently short of tools.

**Tool Module Contract**: Every tool module must expose:
```python
def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
```
The `client` is captured via closure. Tools are registered with `@mcp.tool` — the function docstring becomes the MCP tool description. The `mcp` a module receives is a `ToolRegistrar` (`tools/__init__.py`) that forwards `mcp.tool` to FastMCP with server-wide defaults: a tool returning `str` gets `output_schema=None`, otherwise FastMCP 4 adds a `{"result": string}` output schema and sends every reply twice (`content` and `structuredContent`); every tool gets `annotations=READ_ONLY` (read-only, non-destructive, idempotent, open-world — MCP SDK v2 field names `read_only_hint` …) and `tags` naming its data source(s) — `twse`, `tpex`, `taifex`, `mops`, `tdcc`, `sitca`, `ndc`, `cbc` (`tools.SOURCES`) — from `tools.SOURCE_TAGS`, keyed by module path (the longest prefix wins, e.g. `tools.otc` → `tpex`, `tools.etf.info` → `sitca`, `twse`, `tpex`). A new tool module needs an entry there (registration fails without one), and `tests/unit/test_tool_registration_unit.py` fails when a module's code reaches a source its tags do not name. A deployment can serve a subset of sources by these tags (`TWSE_INCLUDE_SOURCES` / `TWSE_EXCLUDE_SOURCES`, see Configuration). `register_all_tools` returns a `RegisteredTools`: every tool's tags by name (`.tags`, for the prompts) and the tools that passed an output schema (`.structured`; `.text_tools` is the rest, for the response cap). Arguments a tool passes itself win. Put any future all-tools default there rather than on each decorator.

**Layering**: dependencies point down only — `tools/` → `toolkit/` and `services/` → `sources/` → `utils/`. Only `tools/` and `toolkit/` may import `fastmcp`; `utils/` imports none of the other packages, `sources/` only `utils/`, `services/` only `sources/` and `utils/`, `toolkit/` only `utils/`. `tests/unit/test_layering_unit.py` enforces this (in a fresh interpreter too, so transitive imports count) and that each package imports on its own (no circular imports). The Dockerfile copies each top-level package by name; the same test fails if a new package is missing there.

**Gateways** (`sources/`): an endpoint's row layout lives in exactly one gateway, which returns frozen dataclasses — callers never index a raw row (`r[3]`). Look columns up by the published `fields` with `column_index()`; on a renamed/missing column or an unexpected value shape raise `UpstreamFormatError` instead of guessing or returning "no data"; return `None` only when the upstream itself says there is no data. Keep numbers' printed digits with `Decimal` where a tool shows them as published (`utils.printed()` puts the thousands separators back; `utils.plain()` prints every published decimal without them). HTML in cells (MI_INDEX's 漲跌 sign) is stripped in the gateway, never in a tool. The gateway also owns the endpoint's cache policy (e.g. `month_cache_ttl`). Its contract test calls the gateway on live data (`gateway_or_skip` in `tests/helpers.py`), so a format change fails as `UpstreamFormatError`; it checks only that a fixed historical reply (and one per older layout) builds, that one probe row's numbers parse, and the parameter behaviour and labels our code relies on (e.g. the 合計 row label it filters) — never the data's own consistency. Migration is endpoint by endpoint (docs/improvement-plan.md, Phase 3); endpoints parsed in more than one place go first.

**Tool specs**: tools that need no custom code are declared as data and registered in a loop — `CompanyToolSpec(endpoint, name, description)` with `create_company_tool(mcp, spec, client)` for one company's row by stock code, `ListToolSpec(endpoint=, name=, summary=, label=, empty_data_type=, formatter=, filter_field=, name_hint=, normalize=)` with `create_list_tool(mcp, spec, client)` for fetch → optional `name` filter → paginate. `ListToolSpec.description` builds the Args section (`name` when `filter_field` is set, then `limit`/`offset`), so don't hand-write it.

**Structured output** (`toolkit/structured.py`): the four `tools/analytics` tools (`get_stock_screener`, `get_industry_peers`, `get_adjusted_price_history`, `get_technical_indicators`) reply with text and data. Each declares `@mcp.tool(output_schema=output_schema(Result))` for a frozen dataclass `Result` and returns `structured_reply(text, result)` (`-> ToolResult`): `content` is the same text as before — what LLM clients read — and `structuredContent` is the dataclass (dates as ISO `YYYY-MM-DD`, numbers as numbers, `null` for none). Render the text from the dataclass so the two cannot disagree. Every field is `Annotated[..., Field(description=...)]` saying its unit (元、股、%) and calendar (西元／民國), and the dataclass docstring is the schema's description, so write both in Chinese (`tests/unit/test_structured_output_unit.py` checks every field has one). The MCP client validates `structuredContent` against the schema and rejects a successful reply without it, so in these tools a "查無…" outcome with no result to give raises `ToolError` (the one exception to returning 查無 as a normal reply); an empty page or no match is still a result (empty list, `total` 0). They are left out of the response cap (it would drop their schema from tools/list and could cut a reply to text alone), so each bounds its own size: `limit` ≤ 500 (`MAX_ROWS`), 12 months, 60 days. A text tool stays `-> str`.

**Prompts**: each module in `prompts/` holds one prompt — its one public function (private helpers start with `_`), whose name is the prompt's name (client-facing: keep it when editing), docstring its description and parameters its arguments. `prompts.register_all_prompts(mcp, tool_tags)` (called in `server.py` after the tools) registers every module and tags each prompt with the union of the tags of the tools it names as `` `get_xxx(...)` `` (`prompts.TOOL_REFERENCE`); naming a tool that is not registered stops the server. `prompts/` imports no other package of ours (`tests/unit/test_layering_unit.py`). prompts/list lists them in module-name order.

**Auto-Discovery**: `tools/__init__.py` scans direct modules (`tools/broker.py`, `tools/other.py`) and subpackage modules (`tools/company/*.py`, etc.) automatically. No manual registration needed in `server.py` when adding new tool modules. They register in sorted order with the TWSE OpenAPI pass-through packages (`tools.OPENAPI_PACKAGES`: broker, company, market, other, trading) last. That is the tools/list order, and clients that defer tools search it in that order: Anthropic's regex tool search (used by the main client, JackyAIApp, through the MCP connector) returns the first 5 (or `limit`) matches in catalog order, unranked, so 105 broadly worded OpenAPI tools listed first would crowd out the hand-written ones.

**API Client**: `TWSEAPIClient` has instance methods (`fetch_data`, `fetch_company_data`, `fetch_latest_market_data`) and class-method wrappers (`get_data`, `get_company_data`, `get_latest_market_data`) for backward compatibility. Instance methods are preferred. Includes built-in rate limiting: 0.5s between requests to the same site (`throttle_key` — the last three host labels, so every `*.twse.com.tw` host shares one clock), one request at a time per site, different sites in parallel; the client is thread-safe and concurrent identical requests (same `fetch_data` endpoint, or same cached `fetch_json`/`fetch_bytes` call) reach upstream once. A per-site circuit breaker (`utils/circuit_breaker.py`) stops requests to a site after 3 failures in a row (connection error, timeout, 5xx, or an empty / HTML body where JSON was expected) or one refusal (403, 429, MOPS' `FOR SECURITY REASONS` page): for the cooldown (30 s, doubling while the probe after it keeps failing, up to 10 min) calls raise `UpstreamUnavailable` (a `requests.ConnectionError`; tools report 查詢失敗) without sending, and cached responses are still served. Tests that make a site fail on purpose more than twice pass `breaker=CircuitBreaker(threshold=0)`. Work that can chain many requests runs inside `utils.deadline.time_budget(seconds, hint)` (a context manager or decorator): each request's timeout is cut to what is left and, once the budget is spent, the next request raises `DeadlineExceeded` (「超過 N 秒仍未完成（已送出 K 個請求）；hint」) instead of being sent; a timeout caused by that cut is not counted against the site. Current budgets: TAIFEX latest-day walk-back 60 s (`utils/taifex.fetch_period`), `get_futures_intraday` 120 s, TDCC weekly trend 90 s. With the transport's urllib3 `Retry`, a read timeout arrives as `requests.ConnectionError` wrapping `ReadTimeoutError`, not `requests.Timeout`; `circuit_breaker.is_timeout()` recognizes both. For non-OpenAPI sources (legacy TWSE, MIS, TPEx, TAIFEX), use `fetch_json(url, params)` / `get_json(url, params)` which accepts full URLs with query parameters and returns raw JSON (pass `json_body=` to send a JSON POST instead of a GET), and `fetch_bytes(url, data=, method=)` for CSV/zip/HTML bodies.

**Decorators**: Tool functions use decorators from `toolkit/decorators.py` (`from toolkit import handle_api_errors`):
- `@handle_api_errors(use_code_param=True)` — required on every tool. Turns any exception into `ToolError(MSG_QUERY_FAILED)`, which MCP returns with `isError=true` and our Chinese message (left alone, FastMCP would report its English `Error calling tool …`; a middleware cannot do this translation, it only ever sees FastMCP's already-wrapped `ToolError`). Put what a schema can express into the signature instead of checking it in the body: a fixed set of values as `Literal[...]` (defined next to the mapping it indexes, e.g. `utils.institutional.Investor` beside `SORT_LABELS`; `tests/unit/test_argument_validation_unit.py` keeps the two equal), an int range as `toolkit.Limit` / `Offset` or, with an upper bound, `Annotated[int, Field(ge=1, le=MAX_ROWS)]` written out (a helper call in an annotation fails pyright), a date as `toolkit.TradingDate` ("" allowed, the tool's default) or `RequiredTradingDate`. FastMCP rejects other values before the tool runs, and `ArgumentErrorsInChinese` (registered in `server.py`) words the rejection in Chinese (「sort_by 只能是 total、foreign、trust、dealer（收到 'x'）」「date 日期格式錯誤，請使用西元 YYYYMMDD…」「date 日期不存在」). Every date parameter is a Gregorian (西元) YYYYMMDD string and reaches the tool unchanged; the tool or gateway converts it to what the upstream takes with `utils.date_helper`: `roc_date(d)` → `115/09/30` (MOPS 發言日期), `roc_date(d, sep="")` → `1150930` (MOPS t35sc09, TWSE news list; the year padded to three digits), `roc_year_of(d)` → `115`, `slash_date(d)` → `2026/09/30` (TPEx). Don't hand-write `- 1911` or slicing for a request: a new form goes into `date_helper` with a test (`tests/unit/test_date_helper_unit.py`). Replies, by contrast, keep the sources' ROC dates (115/09/30, 115年09月30日, 1150930, 財報期別 115/2 or 115Q2). So that clients don't mix the two: `SERVER_INSTRUCTIONS` in `server.py` (sent once at initialization as MCP `instructions`) states the convention and how to convert; every date / month parameter description says 西元 (a test checks); and a ROC-looking value passed as a date gets its Gregorian equivalent in the error (「date 看起來是民國日期，請換算成西元 YYYYMMDD（民國年 + 1911）：1150930 → 20260930」, `toolkit.validation.describe_date_mismatch`). MOPS `year` parameters (西元或民國) are not dates and keep their own handling. For what a schema cannot express — open sets such as industry codes, rules across parameters (start not after end, span caps), a month that has data — raise `ToolError` yourself (it passes through unchanged); never return failures as ordinary text. Keep tools plain sync functions: FastMCP 4 runs them in a worker thread (`run_in_thread=True`), so a blocking request never stalls the server; tools therefore run concurrently, and modules that keep state across calls must lock it.

**Formatters**: `utils/formatters.py` provides:
- `format_properties_with_values_multiline(data)` — single record dict → multiline string
- `format_multiple_records(records, separator)` — multiple records with separators
- `format_list_response(data, data_type, formatter, limit)` — paginated list with total count

**Paging**: every `limit`/`offset` goes through `utils.Page` (`utils/pagination.py`): `paged = Page(limit, offset).take(rows)`, then `paged.past_end` / `paged.out_of_range(data_type)`, `paged.rows`, `paged.span()` ("顯示第 a–b 筆", empty when everything fits) and `paged.more()` ("... 還有 N 筆，使用 offset=X 查看更多"); pass a unit (`"則"`, `"名"`) where 筆 doesn't fit. `Page(..., max_limit=N)` caps a reply. A bad `limit`/`offset` raises `utils.errors.InvalidArgument`, which `handle_api_errors` reports as `ToolError` with the message as is — use it for any argument error noticed in `utils/` (which cannot import `ToolError`). `tests/unit/test_pagination_unit.py` fails if a tool slices `[offset:offset + limit]` itself.
- `create_simple_list_formatter(name_field, code_field, *extra)` — factory for list formatters

**Company Data Filtering**: `fetch_company_data()` filters by `公司代號`, `Code`, or `權證代號` field matching the `code` parameter.

### Configuration

All configuration in `utils/config.py` reads from environment variables with sensible defaults. See `.env.example` for the full list:
- `TWSE_API_BASE_URL` (default: `https://openapi.twse.com.tw/v1`)
- `TWSE_REQUEST_INTERVAL` (default: `0.5` seconds)
- `TWSE_API_TIMEOUT` (default: `30.0` seconds)
- `TWSE_VERIFY_SSL` (default: `true`) — TLS verification for every upstream. All hosts verify (checked 2026-10-21, Python 3.13); `cpx.cbc.gov.tw` fails only Python 3.13's `VERIFY_X509_STRICT`, so `utils/http_transport.py` verifies it without that flag. `false` turns verification off everywhere (escape hatch for a TLS-intercepting proxy)
- `TWSE_CACHE_TTL` (default: `60` seconds — in-memory cache for `fetch_data` OpenAPI list responses; `0` disables every cache, including the one below)
- `TWSE_RESPONSE_CACHE_MAX_ENTRIES` (default: `256`) — bound on the per-call response cache that `fetch_json` / `fetch_bytes` use when a tool passes `cache_ttl=` (TAIFEX download pages 300s, MOPS 600s, TDCC/CBC 1h, NDC 6h). It stores raw bytes, so callers can't mutate each other's data; only successful responses are cached
- `TWSE_BREAKER_FAILURES` (default: `3`; `0` disables), `TWSE_BREAKER_COOLDOWN` (default: `30` s), `TWSE_BREAKER_MAX_COOLDOWN` (default: `600` s) — the per-site circuit breaker
- `TWSE_INCLUDE_SOURCES` (default: empty = every source), `TWSE_EXCLUDE_SOURCES` (default: empty) — comma-separated source tags (`tools.SOURCES`) this deployment serves; exclude is taken off include. `server.py` passes them to `tools.enabled_sources` (an unknown name stops the server) and `tools.show_only_sources`, which adds FastMCP `Visibility` transforms: a tool is hidden when any source it reads is off (`get_etf_info` needs sitca, twse and tpex) and calling it fails as an unknown tool; a prompt stays while any of its tags is on (its tags are the sources of the tools it names, see Prompts); the server instructions name only the sources served
- `TWSE_MAX_RESPONSE_BYTES` (default: `500000`; `0` turns it off) — last-resort cap on one tool reply (`toolkit.response_limit`, FastMCP's `ResponseLimitingMiddleware`, added in `server.py` after registration, for the text tools only — see Structured output): a longer reply keeps its leading text, cut at a UTF-8 boundary, and ends with `MSG_RESPONSE_TRUNCATED` (「⚠️ 回應超過 500,000 位元組上限，以上只是前段…請縮小查詢」); errors are raised, so never cut. It is not a row limit: most `limit` parameters have no upper bound, and replies measured 2–48 KB normally, 60–280 KB for a whole board at once (every listed stock, every TXO strike), 1.7–5.6 MB only when warrants are included (`get_warrant_basic_info(limit=100000)`, `get_otc_daily`, T86 `category="ALL"`) — those are the replies it cuts
- `DISPLAY_LIMIT` (default: `50`)
- `PYTEST_DELAY_SECONDS` (default: `1.0` — rate limit delay between tests)

## Testing

Two kinds of tests, kept strictly apart:

- **Live contract tests** (`tests/contract/`) call the real third-party APIs. Their only job is to detect an interface change on TWSE / TAIFEX / TPEx / MIS that would break our tools: endpoint gone, response format changed (JSON → CSV/HTML, list → dict), a field or column our tool hardcodes renamed/moved. They must **not** assert on our own logic (pagination, output caps, filtering, message wording), must **not** check that upstream's data is right — sums, balance identities, price × volume, value ranges, units, high ≥ low — that is the source's own job, and must **not** assert that upstream has data today — an empty `[]` from a "latest day only" endpoint is not an interface change (TWSE `t187ap42_L` served `[]` for days after the 2026 Mid-Autumn long weekend). Use `records_or_skip()` from `tests/helpers.py` for such endpoints. Fixed historical dates (`FIXED_DATE`) are expected to have data, so an empty result there is still a failure.
- **Offline unit tests** (`tests/unit/`) test our own logic against canned payloads — via `OfflineClient` (`tests/offline.py`, stubs only the HTTP layer so client-side filtering still runs) or a small stub client. Mark the module `pytestmark = pytest.mark.offline`: `conftest.py` then skips the rate-limit sleep and makes any real HTTP request fail the test. `register_module_tools()` (`tests/helpers.py`) returns a module's tool functions; a tool failure raises `ToolError`, so assert it with `pytest.raises(ToolError, match=...)`. The "Unit Tests" workflow (`.github/workflows/unit-tests.yml`) runs `ruff check`, `pyright` and then them on every PR. Every `zip()` states `strict=`: `True` where the lengths are equal by construction, `False` where a table row may be shorter than its header.

The `conftest.py` autouse fixture sleeps between live tests to avoid rate limiting.

**Test files**:
- `tests/contract/test_api_schemas.py` — parametrized tests that verify fields tools **hardcode with `.get()`** still exist in live API responses. Endpoints are defined in `tests/contract/tool_field_dependencies.py`. Only catches breakage that would silently return "N/A" in a tool.
- `tests/contract/tool_field_dependencies.py` — the source of truth: maps each TWSE OpenAPI endpoint to the list of field names its tool hardcodes. Edit this file when adding or changing hardcoded field access in a tool.
- `tests/contract/test_*.py` — per-category contract tests (history, realtime, otc, taifex, institutional, mops, otc_history, tdcc_macro, etf, listing). For non-TWSE-OpenAPI tools (TAIFEX, OTC, MIS, legacy exchangeReport, MOPS, TDCC, NDC, CBC, SITCA), field assertions live here instead. Use `fetch_bytes_or_skip()` from `tests/helpers.py` for CSV/zip/HTML sources.
- `tests/unit/test_output_limits_unit.py`, `tests/unit/test_summary_row_filtering_unit.py` — offline guards for pagination/output caps and summary-row and placeholder filtering.
- `tests/unit/test_prompt_tool_references_unit.py` — every `get_xxx(` named in `prompts/` must be a registered tool and every keyword it passes a real parameter; update the prompts when removing or renaming a tool.
- `tests/unit/test_prompt_registration_unit.py` — the 9 client-facing prompt names, each prompt is its module's function, prompt tags derived from the tools it names.
- `tests/unit/test_tool_search_unit.py` — simulates Anthropic's regex tool search offline: the words people use for each common tool appear in its text (`WORDS`), 50 common question patterns (several verbatim from live runs) reach the right tool within the first 10 matches, and the OpenAPI pass-through tools are listed last.
- `tests/unit/test_structured_output_unit.py` — every field of a structured result is described, a structured reply passes the client's schema validation, "nothing to return" is an error reply, and `output_schema()` equals the schema FastMCP derives from a return type. `register_module_tools()` hands back the raw `ToolResult` of a structured tool: read `.content[0].text` and `.structured_content`.
- `tests/unit/test_tool_docstrings_unit.py` — every line of a tool's docstring must reach the MCP tool description or a parameter description (catches sections FastMCP drops, e.g. `Returns:`).
- `tests/unit/test_argument_validation_unit.py` — calls the real `server.mcp` with values the schemas reject and checks the Chinese message; every `limit` / `offset` carries its bounds in the schema; every `Literal` matches the mapping it indexes. Calling a tool function directly skips this validation, so test rejected values here, not in the per-tool tests.
- `tests/unit/test_argument_errors_unit.py` — scans every tool function for an argument-error message (`必須是`, `只能是`, `格式錯誤`, …) or a validator's `error` that is `return`ed instead of raised as `ToolError`. "查無…" replies are normal results and stay `return` (except in structured tools, see Structured output).
- `tests/unit/test_contract_scope_unit.py` — keeps `tests/contract/` to interface checks: it fails on arithmetic (other than list/string concatenation and `len(...) ± int`), ordering comparisons other than `len(...)` against an int or a set relation, `a <= b <= c`, and `abs`/`sum`/`min`/`max`/`round` — the shapes data validation takes (sums, identities, price × volume, ranges). Assert messages and f-strings are not scanned. A line that genuinely checks an interface carries `# contract-ok: <reason>` (e.g. the tick file's HHMMSS time). It cannot see equality-shaped data facts ("2330 went ex-dividend on 2025-06-12"); those stay out by the rule above.

**Fixtures** in `conftest.py`: `sample_stock_code` returns `"2330"` (TSMC), `sample_stock_code_with_data` returns `"1210"`.

**CI**: the "API Contract Tests" workflow (`.github/workflows/api-tests.yml`) runs daily at 9:00 AM Taiwan time (or manually, per `run_tests.py` category). On failure it opens an issue "⚠️ Third-party API Contract Test Failed" labeled `api-change,bug,automated`; it auto-closes when tests pass again.

## Adding New Tools

1. Check for overlap first. Don't ship two tools for the same data. Decide overlap from the upstream data, never from tool names or descriptions: fetch both endpoints for the same day and compare row sets, columns and values. If a new source covers an existing tool's data with more range (history, more markets, more columns), make the new tool's period parameters optional so it also serves the "latest" case, give it the existing tool's name, and delete the old one (plus its field dependencies/tests, and update `prompts/`). Tools covering different scopes (e.g. whole-market latest snapshot vs. one stock's month of history) are not overlaps.
2. Add tool function in the appropriate module under `tools/` (or create a new module)
3. Ensure the module has `register_tools(mcp, client)` — it will be auto-discovered
4. Use `@mcp.tool` decorator; the docstring becomes the MCP tool description. FastMCP keeps only the text before the first Google-style section: `Args:` lines become the parameter descriptions and any other section (`Returns:`, `Note:`, …) is dropped, so say what the tool returns before `Args:` (`回傳：…`). Write it with the words people search with, Chinese and English, where the data really holds them (「Put/Call Ratio（PCR、賣買權比）」「日K（歷史股價、K線）」): clients that defer tools find a tool by regex over its name, description and argument text, so a word missing there means the tool is not found. Add the tool's words to `WORDS` in `tests/unit/test_tool_search_unit.py`
5. Use `@handle_api_errors()` (`from toolkit import handle_api_errors`) for standardized error handling; check for empty/None results explicitly and return `MSG_NO_DATA.format(data_type=...)`
6. Use `client.fetch_company_data(endpoint, code)` for company-specific lookups, `client.fetch_data(endpoint)` for general data. If the tool is nothing more than that (or a plain list with an optional name filter), add a `CompanyToolSpec` / `ListToolSpec` to the module's spec list instead of writing a function
7. Format output with utilities from `utils/formatters.py`; page lists with `limit`/`offset` through `utils.Page` (see Paging)
8. **API field tests** — only required when the tool hardcodes field names with `.get("field")`:
   - **TWSE OpenAPI tools** (`fetch_data` / `fetch_company_data`): add the endpoint and its hardcoded fields to `tests/contract/tool_field_dependencies.py`. The parametrized test in `tests/contract/test_api_schemas.py` will pick it up automatically.
   - **Non-TWSE-OpenAPI tools** (TAIFEX, OTC/TPEx, MIS, legacy `exchangeReport`, MOPS, TDCC, NDC, CBC): add a `test_hardcoded_fields_exist` method to the relevant `tests/contract/test_*.py` file.
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

- **TWSE exchangeReport** (`tools/history/`): Legacy JSON endpoints returning `{"stat": "OK", "data": [...]}`. Dates in ROC format — use `utils/date_helper.py` for conversion. `MI_MARGN` uses `tables` array instead of `data` (read through `sources/twse/mi_margn.py`, which finds the two tables by their fields).
- **TWSE OpenAPI listing endpoints** (`tools/company/listing.py`): field names don't say what they hold — read the swagger descriptions. In `/company/newlisting` and `/company/applylistingLocal` the listing date (股票上市買賣日期) is `ApprovedListingDate`; `ListingDate` there is 證期局核准上市契約日期 and nearly always blank. In `/company/applylistingForeign` `ListingDate` is the listing date. `/company/applylistingLocal` serves its rows shifted against their keys (a leading 序號 column, no 核准契約 column): `normalize_local_application` repairs a row when a company name sits under `ApplicationDate`. Both are checked against live data in `tests/contract/test_listing_api.py` (the listing date against the stock's first STOCK_DAY trading day).
- **MIS** (`tools/realtime/`): Single-letter field names (`z`=price, `c`=code, `ex`=market type). Use `tse_` prefix for listed stocks, `otc_` for OTC; tool auto-retries with `otc_` if `tse_` returns no data.
- **TPEx** (`tools/otc/`): Standard REST JSON. Swagger spec at `tpex.org.tw/openapi/swagger.json`. Field names use English (e.g. `SecuritiesCompanyCode`).
- **TAIFEX** (`tools/taifex/`): Requires browser-like `User-Agent` header (the default `stock-mcp/1.0` gets HTML instead of JSON). `TAIFEX_HEADERS`, `decode_and_parse_csv` (cp950; an HTML page — including `<!DOCTYPE HTML` — means no data), `parse_date_range` and `fetch_period` (empty dates → walk back from today, Taiwan time, to the latest day with data; `is_complete` lets the market reports skip a day that only has the overnight 盤後 session so far; generic over what `fetch` returns, raw `ParsedCsv` or a gateway's typed rows) live in `utils/taifex.py`. Download-page gateways (`sources/taifex/`) build on `download_table()`: it posts the form, decodes the CSV and finds the columns by header name; the CSV prints no thousands separators and "-" for no value, so numbers go through `number()` (Decimal) / `count()` (int) and a tool prints them back with `utils.plain()` ("-" for None). Every download page the tools read has its gateway: daily reports, 三大法人 (five pages), large traders, Put/Call Ratio; `tools/taifex/intraday.py` reads the tick zips itself.
  - `openapi.taifex.com.tw` intermittently answers with an endpoint's **CSV** form (Chinese column headers) instead of JSON, even when the request sends `Accept: application/json`. The degradation is per-endpoint and lasts minutes, so `--reruns` does not clear it — measured 2026-08-28, `va01`/`PutCallRatio` served CSV for a stretch and JSON afterwards, while `MarketDataOfMajorInstitutionalTradersDividedByFuturesAndOptionsBytheDate` served CSV on 30/30 consecutive requests as its siblings served JSON. Tests treat this as transient and skip (`_is_taifex_csv_fallback` in `tests/helpers.py`); `test_openapi_still_serves_json_for_some_endpoint` fails if *every* probed endpoint goes CSV, which would mean a real site-wide format change. Tools currently surface these windows as `查詢失敗`.
  - **Tick data** (`tools/taifex/intraday.py`): `dlFutPrevious30DaysSalesData` links one `DailydownloadCSV/Daily_YYYY_MM_DD.zip` per trading day (last 30; the `Dailydownload/` twins are fixed-width reports). Each zip holds one ~45 MB cp950 CSV of every futures trade: 成交日期, 商品代號, 到期月份(週別) (`a/b` = calendar spread), 成交時間 HHMMSS, 成交價格, 成交數量(B+S). A trading day's file starts with its night session (from 15:00 the evening before, dated that evening, past midnight) then the day session 08:45–13:45; before the day session opens the newest file holds only the night session. 成交數量 counts both sides (÷2 = contracts): on 2026-10-16 the night session matched the daily report within 0.3%, the day session was ~12% lower (spread-order legs are not in the file). openapi `TimeAndSalesData` has the latest day only, as ~220 MB JSON — not used.
- **MOPS** (`tools/mops/`, `utils/mops.py`): No public docs. To find a page: the main bundle `https://mops.twse.com.tw/mops/assets/index.js` lists every route as `{path:"/web/<pageId>", name:"<中文頁名>"}`. The SPA's form field names are in per-page JS chunks (`https://mops.twse.com.tw/mops/assets/<pageId>.js`, action `{apiName, type}`); how the body is assembled for a few pages (e.g. `query6_1` needs `subsidiaryCompanyId`) is in index.js — grep it for the page id. `type:"base"` → `POST /mops/api/<apiName>` JSON, reply `{"code", "message", "result"}` (`code` 406 = 查無資料, 500 = bad parameters); `type:"twse"` → legacy `POST mopsov.twse.com.tw/mops/web/<apiName>` form (plus hidden `encodeURIComponent/step/firstin/off` fields), HTML reply. Tables come as nested `titles` + rows; render via `flatten_titles` / `leaf_titles` rather than hardcoding line items (they differ by industry). Legacy `ajax_t100sb02_1` (法說會) only accepts zero-padded months (`09`, not `9`). Legacy pages often have tables without ids and start a new `<table>` every few hundred rows without closing the previous one (`ajax_t35sc09`); `parse_html_tables` handles both. Headers there span two rows (`rowspan` / `colspan`, which `parse_html_tables` does not keep) and carry `<br>` breaks and red notes; `sources/mops/t35sc09.py` strips those and joins a spanned header with the names under it to look columns up by name. An empty t35sc09 range is a page saying 查無所需資料.
- **三大法人** (`utils/institutional.py`; TWSE `tools/history/institutional*.py`, TPEx `tools/otc/history.py`, `tools/otc/institutional_summary.py`): all five tools share `sort_by` (total/foreign/trust/dealer), `side` (buy/sell/abs), `category` and `period`. Per-stock flows of both markets come from their gateways as `InstitutionalFlow` (`sources/institutional.py`), ranked with `rank(flows, lambda f: f.net(sort_by), side)`. T86's columns changed twice (12 fields with 外資 / 自營商 unsplit; 16 from 2014-12-01 with 自營商 split into 自行買賣 / 避險; 19 from 2017-12-18 with 外資自營商 split out); `t86_flows` reads all three by name, so older dates show the groups published then. TPEx `insti/dailyTrade` heads seven groups identically, so `tpex_flows` maps them by order and checks every row's sums. TWSE T86 `selectType`: ALL is ~93% warrants/CBBCs, ALLBUT0999 excludes them (default), 0099P = ETFs, two-digit industry codes pass through; TPEx `sect` EW (default) / EE (ETF) / AL. `category="stock"` drops 00-prefixed codes — on both markets every ETF code starts with 00 and every 00 code is an ETF (contract-tested). TWSE BFI82U: no `dayDate` → latest day; `type=week` needs the week's first trading day as `weekDate` (Monday, or Tuesday when Monday is a holiday — the tool walks forward); `type=month` needs a `monthDate` (none → HTML). TPEx `insti/summary`: `type` Daily/Weekly/Monthly with any day of that week/month, `prod` 1 上櫃股票 / 0 上櫃有價證券.
- **TPEx website** (`tools/otc/`): `www.tpex.org.tw/www/zh-tw/...?response=json` with `date=YYYY/MM/DD`; rows are in `tables[0].data` (margin/balance adds market totals in `tables[0].summary`). Every endpoint the tools read has a gateway in `sources/tpex/`. `insti/dailyTrade` repeats identical column names for 7 買進/賣出/買賣超 groups — the contract test checks the group order via their sums.
- **NDC** (`tools/macro/ndc_indicators.py`): `index.ndc.gov.tw` is behind a Cloudflare bot block — don't try to get around it. Use the fixed `ws.ndc.gov.tw/Download.ashx` links from data.gov.tw datasets 6099 (zip of CSVs) and 6100 (PMI CSV); if NDC re-points them the contract tests fail.
- **CBC** (`tools/macro/exchange_rates.py`): `cpx.cbc.gov.tw/API/DataAPI/Get?FileName=BP01D01`; the file is refreshed about monthly, so the latest weeks may be absent.
- **SITCA ETF zone** (`utils/sitca.py`): each query page (`etf_info.aspx`, `etf_statement.aspx`) is an ASP.NET form, but its 查詢 button only sets an iframe to a GET result page — read those directly: `etf_info2.aspx` / `etf_statement2.aspx?txtYM=YYYYMM&txtcomid=&txtfund=&txtemcode=<code>,&txtkeyword=&txtR1=1&txtR2=1` (empty `txtemcode` = every ETF). `txtYM` must be in the page's `ddlYM` select. The result grid is nested in a layout table, so parse it by id (`ctl00_ContentPlaceHolder1_GridView1`). Months before ~2024 have `-` in every 證券代號, so a code finds nothing there: resolve the code to its 基金統編 in the newest month and query older months with `txtfund=<統編>,`. Futures-trust ETFs (U and some L/R) and foreign-currency codes (K) are not SITCA funds. Each request takes 2–4 s server-side.
- **SITCA 基金投資明細** (`utils/sitca.py`, `tools/etf/holdings.py`): `www.sitca.org.tw/ROC/Industry/IN2629.aspx` (monthly top 10) and `IN2630.aspx` (quarterly, every holding >1% of NAV) are ASP.NET postback forms. Querying a period other than the default one requires the period postback first (`__EVENTTARGET=ctl00$ContentPlaceHolder1$ddlQ_YM`) — without it the server silently returns the first issuer's (兆豐) funds. Then POST the query with that reply's hidden fields and only the enabled fields (`ddlQ_YM`, `rdo1=rbClass`, `ddlQ_Class`, `BtnQuery`). No cookie needed, so GET + both POSTs are cached. The result table has no id, closes header `<td>` with `</th>`, and rowspans the fund name. Rows carry fund names only: the tool resolves the code in the ETF zone (`基金名稱`, `類型代號`; for a past period the names of that month, found by 基金統編, because funds get renamed) and compares `fund_name_key` (drops the ` (本基金…)` disclaimer and the ETF zone's `-新台幣(配息)` share-class suffix). Exact match only — 正向2倍 vs 反向1倍 differ by two characters. Checked 2022-01 / 2025-01 / 2026-08: every non-leveraged/inverse ETF matched except two absent from that month's filing; leveraged/inverse ETFs are not listed (futures and cash).
- **MIS ETF feed** (`tools/etf/daily_nav.py`): `mis.twse.com.tw/stock/data/all_etf.txt` — `a1[]` per issuer, each `msgArray[]` with TWSE's 介接格式 fields a–k (code, name, units, unit change, price, est. NAV, premium %, prior NAV or `未結出`, date, time, type). Issuers send numbers or strings inconsistently.
- **TDCC query page** (`tools/tdcc/shareholding_distribution.py`): `www.tdcc.com.tw/portal/zh/smWeb/qryStock` has no CAPTCHA, but it is a stateful form: GET the page (sets `JSESSIONID`; hidden `SYNCHRONIZER_TOKEN`, `firDate`, and a `scaDate` list of ~51 weeks newest first), then POST `SYNCHRONIZER_TOKEN`, `SYNCHRONIZER_URI=/portal/zh/smWeb/qryStock`, `method=submit`, `firDate`, `scaDate`, `sqlMethod=StockNo`, `stockNo`, `stockName`. Tokens are single-use and every reply carries the next one, so the tool chains them inside one `requests.Session` (`fetch_bytes(..., session=)`, which also bypasses the response cache) and reloads the page if a reply has none. Unknown code → `查無此資料`. Compared with the open-data CSV (2026-10-02; 2330, 6488, 0050): levels 1–15 and the total are identical; only 差異數調整 differs (page keeps the sign and drops the row when zero), so the trend ignores it. Past weeks are immutable and kept in an in-process cache.
