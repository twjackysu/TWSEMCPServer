# 改善計畫（2026-10-21 review）

以「寫出 Design Patterns 的作者們會怎麼做」為標準，對整個 repo 做的 review 與分階段計畫。
每個階段可獨立成一個 PR；完成後在下方「進度」打勾並註記 PR。

**基準：FastMCP 4.1.3（#107）。** 之後的改進一律先找 FastMCP 4 的原生機制（`@mcp.tool` 參數、
middleware、transform），沒有才自己寫。對照表見「FastMCP 4 對照」。

## 進度

- [x] P0 修正（#106，2026-10-21 合併）：
  P0-1 thread offload；P0-2 失敗改 `ToolError`；P0-3 profitability 排序；P0-4 註冊 fail-fast；
  P0-5 PR 跑 unit test、CI Python 版本。另含 per-site thread-safe 節流、single-flight。
- [x] 套件升級：FastMCP 2.12.3 → 4.1.3、mcp 1.27 → 2.3 等（#107，2026-10-21 合併）
- [x] FastMCP 4 對齊（#109，2026-10-21 合併）：`handle_api_errors` 改回同步、只做錯誤轉換；`ToolRegistrar`
  讓文字型 tool 設 `output_schema=None`
- [x] P0 收尾（#110）：參數錯誤改 `raise ToolError`（32 個模組 63 處，訊息不變，
  `test_argument_errors_unit.py` 把關）；`get_futures_intraday` 共用快取加鎖（#106 漏掉的並行 race）
- [x] 開始 P1 前的掃描與順帶修正：TDCC 逐週趨勢把錯誤頁當成沒資料（#111）；上市日期讀錯欄位、
  `applylistingLocal` 整排錯位（#112）
- [ ] Phase 0 剩餘：`ruff check` 進 CI
- [x] P1-7 傳輸層（#113）：每網站一個連線池 Session、全部網站開啟 TLS 驗證、Retry（間隔、Retry-After 上限）
- [ ] Phase 1 剩餘：circuit breaker（見「防止被鎖 IP」）

**P1 的 PR 順序**（每項一個 PR）：
1. ✅ P1-7 傳輸層（上一行）。
2. ✅ P1-9 + P1-11（#114）：`decorators.py`、`tool_factory.py` 移到新的 `toolkit/`，`utils/` 不再 import
   fastmcp、循環 import 解掉（`test_layering_unit.py` 把關）；7 份位置 tuple 改成 `CompanyToolSpec` /
   `ListToolSpec`。`tools/list` 與 main 逐字相同。
3. ✅ P1-8（#115）：`utils.Page` 取代 13 個模組裡 16 段手刻分頁與 `format_list_response` 內的分頁；
   錯誤的 `limit`/`offset` 丟 `utils.errors.InvalidArgument` → `ToolError`；profitability 改成
   `limit`/`offset`（breaking，記在 PR 說明；repo 沒有 CHANGELOG）。`test_pagination_unit.py` 擋手刻分頁。
4. P1-6 / P1-10（Phase 3 起點）：被重複解析的 STOCK_DAY、MI_INDEX、TWT49U、BWIBBU_d 各收成一個
   gateway；T86 改依 `fields` 取欄位，TPEx dailyTrade 走 Adapter，兩市場共用排行與呈現。
   - ✅ STOCK_DAY（#116）：`sources/twse/stock_day.py`；同時建立 `sources/`、`services/` 兩層，
     `price_series` 移到 `services/`；`column_index`、`month_cache_ttl`、`utils/parse.py`、
     `UpstreamFormatError` 供後續 gateway 共用。tool 輸出與 main 逐字相同。
   - ✅ MI_INDEX（#117）：`sources/twse/mi_index.py`（行情、指數、產業成員）；`market_snapshot` 移到
     `services/`；`day_cache_ttl`、`utils.printed()`。
   - ✅ TWT49U（#118）：`sources/twse/twt49u.py`；`get_exright_results_history` 與還原權息共用，
     `stat` 原樣保留給「查無」訊息。2024–2026 共 3,922 列與舊版逐字相同。
   - ✅ BWIBBU_d（#119）：`sources/twse/bwibbu_d.py`；`get_stock_valuation_ratios` 與 `market_snapshot`
     共用。兩個完整交易日（1,083 + 1,031 檔）與上市全部選股結果與舊版逐字相同。
   - [ ] T86 + TPEx dailyTrade（Adapter）
- [ ] Phase 2 共用核心
- [ ] Phase 3 來源層 + 領域層
- [ ] Phase 4 MCP 介面
- [ ] Phase 5 打包

## 結論

**保留的優點**：上游怪癖都寫在註解（T86 selectType、TAIFEX CSV fallback、MOPS 406）；contract / unit
測試嚴格分離；「API 掛掉不可偽裝成查無資料」的錯誤哲學。

**核心問題**：177 個 Transaction Script。每個 tool 函式自己做「驗證 → 打 API → 用 `r[3]` 解析 →
排序／篩選 → 分頁 → 拼字串」。正確風格已存在於 `utils/price_series.py`（frozen `Bar` / `ExRightEvent`）
與 `utils/market_snapshot.py`（`StockSnapshot`），只是沒推廣，兩種風格並存。

GoF 兩句核心：「對介面寫程式，不對實作寫程式」、「優先組合而非繼承」。缺的不是更多 pattern，是**分層**。

## 實測數字（2026-10-21）

| 項目 | 數字 |
|---|---|
| 註冊 tool | 177 個，tool schema 約 120K 字元（每個 client 每次對話都載入） |
| 位置索引 `r[n]` / `row[n]` | tools/ + utils/ 共 398 處 |
| 各自實作的數字解析 | 9 份，語意不一：`to_int` 髒值回 0，`_num` 回 None |
| 手刻分頁 | tools/ 13 個檔（`format_list_response` 沒被用） |
| 「日期格式錯誤」訊息副本 | 13 份 |
| 參數用 `Literal` 列舉 | 0 |
| unit test | 233 個，2.1 秒全過，但 PR 不跑 |
| 3 個同步 tool 並發（各 1 秒） | 3.02 秒：序列化，event loop 被擋 |

## 發現

### P0：執行期正確性

1. **同步 tool 擋住整個 server**。FastMCP 2.12.3 `FunctionTool.run` 在 event loop 上直接呼叫同步函式；
   177 個 tool 全同步，含 `requests` + `time.sleep` 節流。HTTP 模式下一次 TAIFEX「往回找最新交易日」
   （最多 12 次請求）或 45MB tick zip 會讓所有 client 一起卡住。（FastMCP 4 起同步 tool 預設在
   threadpool 執行，見「FastMCP 4 對照」。）
2. **錯誤當成功回傳**。`handle_api_errors` 回傳 `"查詢失敗: ..."` 字串 → MCP `isError=false`，client 無法
   程式化分辨失敗。參數錯誤（13 處「日期格式錯誤」、`check_choice`）同樣。應 `raise ToolError`。
3. **靜默改輸入 → 結果錯**。`get_company_profitability_analysis_summary`：docstring 叫 LLM 傳 `毛利率(%)`，
   程式只收 `毛利率(%)(營業毛利)/(營業收入)`，不符就默默依「公司代號」排序；docstring 寫預設 `'asc'`，
   簽名是 `"desc"`。
4. **tool 模組載入失敗被吞**。`register_all_tools` 只 log，server 照常啟動、少一整組 tool。
5. **PR 沒有 CI 把關**。`api-tests.yml` 只排程跑 contract；`ghcr-publish.yaml` 只 build。CI 用
   Python 3.12，pyproject 要 `>=3.13`；`API_REQUEST_DELAY` 沒有程式讀取。

### P1：設計

6. **沒有資料源層，同端點多處解析**：STOCK_DAY ×2、MI_INDEX ×3、TWT49U ×2、BWIBBU_d ×2。上游動一欄要修
   2–3 處，contract test 只守一處。T86 回應自帶 19 個 `fields`，程式卻用 `IDX_* = 0..18` 寫死位置。
7. **`TWSEAPIClient` 是 God Object**：傳輸、節流、兩套快取、OpenAPI 正規化、公司篩選、Singleton、相容
   classmethod 全在一類。後果：全域單一節流時鐘（查 MOPS 等 TAIFEX）；`time.time()` 計時；每次新建連線、
   無 Session、無 retry；`verify_ssl=False` 套用到所有 host。（更正：2026-10-21 實測 13 個 host 在
   Python 3.13 下都能驗證，包括 TWSE；只有 `cpx.cbc.gov.tw` 過不了 3.13 的 `VERIFY_X509_STRICT`。）
8. **分頁兩種寫法**：多數 `limit/offset`，profitability 用 `page_size/page_number`。（已修，#115：`utils.Page`）
9. **依賴方向反**：`utils/tool_factory.py` import `fastmcp`（基礎層依賴呈現層）；`utils/__init__` ↔
   `tool_factory` 循環 import。（已修，#114：移到 `toolkit/`）
10. **測試只能比對字串**：邏輯和呈現綁死，unit test 寫 `assert "外資:120（不含自營商 100…" in text`。
11. **`SIMPLE_LIST_TOOLS` 用 8 欄位置 tuple**，欄位順序靠註解記。（已修，#114：`CompanyToolSpec` / `ListToolSpec`）

### P2：產品與維運

12. **177 tools 全曝露**：吃 client context，LLM 易選錯。無 tags、無 `mount`。
    另外每個 `-> str` 的 tool 都自動帶 `{"result": string}` 的 outputSchema，`tools/call` 會把同一份文字
    放在 `content` 和 `structuredContent` 各回一次。
13. **無 tool annotations**：全唯讀卻沒標 `readOnlyHint` / `openWorldHint` / `idempotentHint`。
14. **打包**：Dockerfile 裝用不到的 Node.js、root 執行、單階段；`requirements*.txt` 與 `uv.lock` 重複；
    `httpx`、`mcp[cli]` 宣告但未直接用；無 ruff / pyright。
15. **prompts 手寫註冊**：`server.py` 9 個 wrapper，tools 卻自動發現。

## 目標架構

```
tools/       MCP 介面層：薄。Literal 參數、ToolError、annotations、tags
render/      呈現層：dataclass → 文字（Template Method：表頭／列／分頁尾）
services/    服務層：純函式 rank、paginate、adjust、screen
domain/      領域層：frozen dataclass + Value Object（TradingDate、StockCode、Market）
sources/     來源層：每端點一個 Gateway，全專案唯一知道 r[3] 是開盤價的地方
http/        傳輸層：Session ← Retry ← Throttle(per site) ← Cache（Decorator 鏈）
```

| 問題 | Pattern |
|---|---|
| 同端點多處解析、398 個 `r[n]` | Gateway / Repository |
| T86 與 TPEx dailyTrade 兩套排行 | Adapter → 共同 `InstitutionalFlow`，一套 rank + render |
| God client、全域節流、全域關 TLS | Decorator 鏈 + Strategy（每個 site 一份 `HostPolicy`） |
| 13 份分頁、13 份日期驗證 | Value Object（`TradingDate`、`Page`） |
| 錯誤當成功回傳 | 例外階層，只在 tool 邊界轉 `ToolError` |

### 示範：傳輸層

```python
@dataclass(frozen=True)
class HostPolicy:                       # Strategy
    interval: float = 0.5
    verify_tls: bool = True             # 只有 www.twse.com.tw 設 False
    headers: Mapping[str, str] = MappingProxyType({})

class Throttled:                        # Decorator：每個 site 一把鎖、一個時鐘，thread-safe
    def get(self, req: Request) -> bytes:
        site = site_of(req.url)
        with self._locks[site]:
            self._wait(site)            # time.monotonic()
            try:
                return self._inner.get(req)
            finally:
                self._stamp[site] = time.monotonic()

http = Cached(Throttled(SessionTransport(POLICIES), POLICIES), max_entries=256)
```

### 示範：領域層 + Gateway（欄名為示意）

```python
@dataclass(frozen=True, slots=True)
class InstitutionalFlow:
    code: str
    name: str
    foreign: int   # 含外資自營商
    trust: int
    dealer: int
    total: int

class T86Gateway:                                       # sources/twse_rwd/t86.py
    def daily(self, day: TradingDate | None, select_type: str) -> Dated[list[InstitutionalFlow]]:
        resp = self._http.get_json(T86_URL, {"response": "json", "selectType": select_type, **day_param(day)})
        col = ColumnMap(resp["fields"])                 # 依欄名取值，上游搬欄位也不壞
        return Dated(resp["date"], [
            InstitutionalFlow(
                code=r[col["證券代號"]].strip(), name=r[col["證券名稱"]].strip(),
                foreign=int_or_zero(r[col["外陸資買賣超股數(不含外資自營商)"]]) + int_or_zero(r[col["外資自營商買賣超股數"]]),
                trust=int_or_zero(r[col["投信買賣超股數"]]),
                dealer=int_or_zero(r[col["自營商買賣超股數"]]),
                total=int_or_zero(r[col["三大法人買賣超股數"]]),
            ) for r in resp["data"] if len(r) == len(col)
        ])

class TpexInstiGateway:                                 # 7 組欄名重複，只能靠位置：Adapter 藏起來
    _NET = {"foreign": 10, "trust": 13, "dealer": 22, "total": 23}
    def daily(self, day, sect) -> Dated[list[InstitutionalFlow]]: ...
```

### 示範：Tool 層（約 140 行 → 8 行，排行與呈現和上櫃共用）

```python
Investor = Literal["total", "foreign", "trust", "dealer"]
Side = Literal["abs", "buy", "sell"]
READ_ONLY = ToolAnnotations(readOnlyHint=True, openWorldHint=True, idempotentHint=True)

# FastMCP 4：同步 tool 自動在 threadpool 跑；timeout 只對 threadpool／async 有效
@mcp.tool(annotations=READ_ONLY, tags={"twse", "institutional"}, timeout=60, output_schema=None)
@handle_api_errors()    # 同步 decorator：例外 → ToolError(查詢失敗: …)，isError=true
def get_twse_institutional_investors_summary(
    date: str = "", category: str = "", sort_by: Investor = "total", side: Side = "abs",
    limit: Annotated[int, Field(ge=1, le=500)] = 50, offset: Annotated[int, Field(ge=0)] = 0,
) -> str:
    """（docstring 不變）"""
    snap = twse.t86.daily(TradingDate.parse_optional(date), select_type(category))
    ranked = rank(snap.value, by=sort_by, side=side)
    return render.institutional_ranking(snap, ranked, Page(limit, offset), by=sort_by, side=side)
```

分層後 unit test 斷言 `InstitutionalFlow`，不比字串；呈現層 snapshot 測一次。

## 分階段計畫

### Phase 0：護欄（小）
- 新 `ci.yml`：PR 跑 unit test（之後加 `ruff check`）；修 Python 版本；刪 `API_REQUEST_DELAY`。
- `register_all_tools` fail-fast，加測試確認全部 tool 模組註冊成功。
- 修 P0-3 profitability bug。
- 驗收：PR 頁面出現 unit 綠燈；故意弄壞一個模組 → server 啟動失敗。

### Phase 1：執行期
- ✅ 同步 tool 丟 thread；失敗回 `isError=true`（`ToolError`）（#106；FastMCP 4 起 thread 由框架負責）。
- ✅ client thread-safe：per-site 節流鎖、`monotonic` 計時、single-flight（並發相同請求只打一次上游）。
- ✅ 每網站一個連線池 Session（cookie 每次清掉，維持無狀態）、全部網站開啟 TLS 驗證（央行只拿掉
  `VERIFY_X509_STRICT`）、Retry：502/503/504 與連線失敗最多 2 次，間隔至少 1 秒再 2 秒加 jitter，
  帶 `Retry-After` 的 413/429/503 照它等、超過 10 秒就放棄（`utils/http_transport.py`，#113）。
  上游重試放在 HTTP 層，不用 FastMCP 的 `RetryMiddleware`（見對照表）。
- 剩餘：circuit breaker。
- 剩餘：慢的 tool 設 `timeout=`（TAIFEX tick zip、`fetch_period` 往回找、TDCC 13 週）；超過一兩分鐘的
  考慮 `task=True` 背景任務。

### Phase 2：共用核心
- `utils/parse.py`：`int_or_zero` / `int_or_none` / `float_or_none` 取代 9 份數字解析。
- `TradingDate` 取代 13 份日期驗證（驗證失敗丟 `InvalidArgument`）；`Page` 取代手刻分頁已在 #115 完成。
- 列舉參數全改 `Literal`、範圍用 `Annotated[int, Field(ge=…, le=…)]`：FastMCP 4 依 schema 驗證，錯了直接回
  `isError`，不必在函式裡手寫檢查（手寫檢查目前已 `raise ToolError`，#110；改成 schema 後可刪掉那些檢查）。
- 統一 profitability 分頁寫法（參數改名屬 breaking，記 changelog）。
- 參數說明寫在 docstring 的 `Args:`：FastMCP 4 會搬進各參數的 `description`；`Returns:` 等其他段落會被丟掉，
  回傳內容寫在 `Args:` 之前（`回傳：…`，#107 已改，`test_tool_docstrings_unit.py` 把關）。
- 驗收：grep 計數 9→1、13→1、13→0。

### Phase 3：來源層 + 領域層（Strangler Fig，一端點一 PR）
- 順序：先做被重複解析的 STOCK_DAY、MI_INDEX、TWT49U、BWIBBU_d；再做 T86 + TPEx（Adapter 示範）；其餘逐步。
- contract test 改測 gateway：真實回應要能建出 dataclass（比「欄位存在」強，型別／單位變了也抓得到）。
- 105 個 OpenAPI 透傳 tool 不動，`create_company_tool` 已是對的抽象。
- 驗收：`r[n]` 只出現在 `sources/`，tools/ 內 0 處。

### Phase 4：MCP 介面（全部用 FastMCP 4 原生機制）
- 全部 tool 加 `@mcp.tool(annotations=READ_ONLY)`、依來源加 `tags`（`twse`、`tpex`、`taifex`、`mops`…）。
  `create_company_tool` / `create_list_tool` 一併帶上。
- 讓使用者只載入需要的子集：`Visibility` transform 依 tags 開關（取代原本想自己做的 `MCP_INCLUDE_TAGS`
  過濾），環境變數只負責決定要加哪些 `Visibility`。
- 177 個 tool 吃 context：評估 `RegexSearchTransform`（`list_tools` 只剩 `search_tools` + `call_tool`，
  需要時再搜）。**不要用 `BM25SearchTransform`**：它的 tokenizer（`[^\W_]{2,}`）不切中文，整段中文描述
  變成一個詞，實測「外資 買超 排行 上市」排第一的是期貨月統計；regex `外資.*買超` 則正確找到三支三大法人
  tool。要 BM25 就得自訂 `BaseSearchTransform`，用中文 bigram 斷詞。先確認主要 client 能好好用
  `call_tool` 代理再上線。
- 文字型 tool 設 `output_schema=None`，`tools/call` 不再把同一份文字在 `structuredContent` 多回一次；
  screener、技術指標這類改回真的結構化資料（dataclass → output schema）。
- `ResponseLimitingMiddleware` 當最後保險（各 tool 仍自己用 `cap_rows` 控制筆數）。
- prompts 改自動發現（FastMCP 4 的 prompt 回傳 `str`，#107 已改）。

### Phase 5：打包
- Dockerfile 多階段、non-root、去 Node.js、`--no-dev`、HEALTHCHECK。
- 移除 `requirements*.txt` 與未用依賴（`httpx`、`mcp[cli]` 在 #107 後仍沒有直接使用）；pyright basic 模式。

## FastMCP 4 對照

2026-10-21 在 FastMCP 4.1.3 上實測（in-memory `Client`）：

| 項目 | FastMCP 4 行為 | 對本 repo 的影響 |
|---|---|---|
| 同步 tool | 預設 `run_in_thread=True`，在 threadpool 執行；3 個無 decorator 的同步 tool 並發 0.39 秒 | `handle_api_errors` 的 async wrapper + `anyio.to_thread` 變多餘 → 改回同步，只做錯誤轉換；`tests/helpers.py` 的 `_run_sync` 跟著拿掉 |
| 未處理的例外 | 自動 `isError=true`，訊息是英文 `Error calling tool 'x': …` | 中文「查詢失敗」與 log 仍要 `handle_api_errors` |
| `on_call_tool` middleware | 看不到 tool 的原始例外，FastMCP 已先包成上面那個 `ToolError` | 不能用 middleware 取代 177 個 decorator 來轉中文訊息；decorator 留在 tool 邊界 |
| `@mcp.tool` 新參數 | `annotations`、`tags`、`timeout`、`task`、`version`、`title`、`output_schema`、`run_in_thread` | Phase 1（timeout/task）、Phase 4（annotations/tags/output_schema） |
| `-> str` 的 outputSchema | 每個 tool 自動 `{"result": string}`，回應同一份文字兩次；`output_schema=None` 可關 | Phase 4 |
| 參數驗證 | 依 schema（`Literal`、`Field`）驗證，`additionalProperties: false`；docstring `Args:` → 參數說明 | Phase 2 |
| Search transform | `RegexSearchTransform` 中文可用；`BM25SearchTransform` 不切中文 | Phase 4 |
| `Visibility` transform | 依 name / tags / version 開關 tool | Phase 4 |
| `ResponseLimitingMiddleware` | 依位元組截斷 tool 回應 | Phase 4（保險） |
| `RetryMiddleware` | 重跑整個 tool 呼叫，只認內建 `ConnectionError` / `TimeoutError`；`requests` 的例外不是它們的子類，而且已被 `handle_api_errors` 轉成 `ToolError` | 不用；上游重試放 HTTP 層（Phase 1） |
| `ResponseCachingMiddleware` | 快取整個 `tools/call` 結果（TTL） | 先不用：「最新交易日」類 tool 的新鮮度要看來源，快取留在 client 層依來源設定 TTL |
| OpenAPI provider | 可從 swagger 產生 tool | 先不換：105 個 OpenAPI tool 有公司代號篩選與中文訊息，`create_company_tool` 已夠薄 |
| 已移除的 API | `FastMCP.get_tools()`（改 `get_tool(name)` / `list_tools()`）、`fastmcp.prompts.prompt`、`fastmcp dev server.py`（改 `fastmcp dev inspector`） | #107 已改 |

## 防止被第三方鎖 IP

問題不在 `time.sleep`，在於睡在 event loop 上。工具改在 worker thread 執行後（FastMCP 4 預設如此），
節流等待只擋那一個請求。節流本身仍然需要；能再做的事，依效果排序：

1. **少打請求（最有效）**
   - 已有：記憶體快取、整批端點抓一次本地篩選。
   - 已加：single-flight，並發的相同請求只打一次上游（`fetch_data` 與有 `cache_ttl` 的呼叫）。
   - 可加：不變的歷史資料（過去月份日K、過去週的集保）存磁碟快取（sqlite / diskcache），重啟不用重抓。
2. **控制速率形狀**
   - 已加：依網站（`throttle_key`，`*.twse.com.tw` 共用一個時鐘）一次一個請求、間隔 0.5 秒。
   - 可加：per-site 設定間隔或 token bucket。社群經驗值（twstock 等套件文件，非官方）是證交所約
     每 5 秒 3 個請求；目前 0.5 秒＝每 5 秒最多 10 個，對 `twse.com.tw` 可能偏快，應可個別調整。
3. **被限流時退讓**
   - 已加：429/503 尊重 `Retry-After`（超過 10 秒就放棄，不重試）；沒有 `Retry-After` 的 429 不重試；
     502/503/504 重試時間隔至少 1 秒、再 2 秒，加 jitter（#113）。
   - 可加：per-site circuit breaker：連續失敗或偵測到封鎖頁（例如 MOPS 的 `FOR SECURITY REASONS`）就停打
     該網站一段冷卻時間，直接回錯誤。被擋時繼續打只會延長封鎖。
4. **連線重用**：已加，每網站一個 `requests.Session` 連線池（#113）。
5. **不做**：用代理池輪換 IP 規避封鎖，違反資料來源的使用條款。

## 不要做的事

- 一次重寫 177 個 tool：一端點一 PR，contract test 當安全網。
- 引入 DI 框架：`register_tools(mcp, client)` closure 注入已夠。
- 先全面 async（httpx）：FastMCP 4 已把同步 tool 放進 threadpool，改 async 沒有額外效益。
- 自己做 FastMCP 已有的東西：tool 過濾用 `Visibility`、timeout 用 `@mcp.tool(timeout=)`、輸出上限用
  `ResponseLimitingMiddleware`。
- 為 pattern 而 pattern：透傳型 tool 就該是一行 factory。
