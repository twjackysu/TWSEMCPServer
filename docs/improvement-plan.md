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
- [x] Phase 0 `ruff check` 進 CI（#124）：ruff 0.17.1 固定版本，只開抓 bug 的規則（F、E4/E7/E9、B）；
  先修掉現有 38 個。ruff 自己的預設規則還會報約 680 個型別寫法與 import 排序，屬於風格，留待 Phase 2 一起處理
- [x] P1-7 傳輸層（#113）：每網站一個連線池 Session、全部網站開啟 TLS 驗證、Retry（間隔、Retry-After 上限）
- [x] Phase 1 circuit breaker（#122）：每個網站連續 3 次失敗、或一次被擋（403／429／封鎖頁）就冷卻
  30 秒，冷卻後的試探再失敗就加倍（上限 10 分鐘）；冷卻中直接回錯誤、快取照常可用（`utils/circuit_breaker.py`）
- [x] Phase 1 慢的 tool 的時間上限（#123）：**不用 `@mcp.tool(timeout=)`**——FastMCP 4 對同步 tool 擋不住
  （實測 timeout=1 的 3 秒工具 3.2 秒才回，結果被丟掉）。改用 `utils/deadline.time_budget`：預算內每個上游
  請求的 timeout 縮成剩餘時間，用完就不再送。TAIFEX 往回找最新交易日 60 秒、tick zip 120 秒、TDCC 逐週 90 秒

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
   - ✅ T86 + TPEx dailyTrade（#121）：兩個 gateway 都回 `InstitutionalFlow`（`sources/institutional.py`），排行共用
     `rank(flows, f.net(sort_by))`。T86 依欄名讀三種歷史格式（12 欄、2014-12-01 起 16 欄、2017-12-18 起 19 欄），
     修好 2017-12-18 前的日期一律「查無」；TPEx 7 組同名欄位依順序對應（Adapter），逐列檢查加總。呈現仍各自保留（上市排行沒有拆外資自營商、
     自營商自行／避險），統一會改變輸出，另議。
- [x] Phase 2 共用核心（#125 Literal／Field、#126 TradingDate、#127 日期慣例、#128 數字解析）
- [ ] Phase 3 來源層 + 領域層
- [ ] Phase 4 MCP 介面（進行中：#109 output_schema、#127 server instructions、#129 annotations／tags、
  #130 依來源開關工具、#131 prompts 自動註冊、#132 回應大小上限；下一步搜尋式工具清單、結構化輸出）
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
15. **prompts 手寫註冊**：`server.py` 9 個 wrapper，tools 卻自動發現。（已修，#131：`prompts.register_all_prompts`）

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

# FastMCP 4：同步 tool 自動在 threadpool 跑。timeout= 擋不住同步 tool（見 Phase 1），時間上限用 time_budget
@mcp.tool(annotations=READ_ONLY, tags={"twse", "institutional"}, output_schema=None)
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
- ✅ 每個網站一個 circuit breaker（`utils/circuit_breaker.py`，#122）：連續 3 次失敗（連線失敗、逾時、
  5xx、期待 JSON 卻拿到空白或 HTML）或一次被擋（403、429、MOPS 封鎖頁）就冷卻 30 秒；冷卻中不送請求、
  直接回 `UpstreamUnavailable`，快取照常可用；冷卻後放一個請求試探，失敗就加倍冷卻（上限 10 分鐘），
  成功就恢復。TAIFEX openapi 偶發的 CSV 形式不計入（它只影響單一端點）。
- ✅ 慢的 tool 的時間上限（`utils/deadline.py`，#123）。原本打算用 `@mcp.tool(timeout=)`，實測 FastMCP 4.1.3
  做不到：同步 tool 跑在 `anyio.to_thread.run_sync`（不放棄執行緒），取消要等執行緒做完才生效——timeout=1 的
  3 秒工具 3.2 秒才回，回的是逾時錯誤（英文），做完的結果被丟掉。async 包一層並 `abandon_on_cancel=True`
  可以準時回，但背景執行緒會繼續打上游、佔住網站鎖。所以改在花時間的地方限制：`time_budget(秒數, 提示)`
  區塊內，`TWSEAPIClient` 把每個請求的 timeout 縮成剩餘時間，用完就丟 `DeadlineExceeded`（「超過 N 秒仍未完成
  （已送出 K 個請求）；提示」），不留背景工作。TAIFEX 往回找最新交易日 60 秒、tick zip 120 秒、TDCC 逐週 90 秒
  （正常各約 1、3、8 秒）。預算縮短而造成的逾時不算網站失敗，不計入 circuit breaker。
  另外發現：掛了 urllib3 `Retry` 之後，讀取逾時是以 `requests.ConnectionError`（Max retries exceeded …
  ReadTimeoutError）拋出，不是 `requests.Timeout`；`circuit_breaker.is_timeout` 兩種都認得。
- 之後可考慮：超過一兩分鐘的工作改 `task=True` 背景任務（需要 client 支援 MCP tasks）。

### Phase 2：共用核心
- ✅ `utils/parse.py` 取代 9 份數字解析（#128）：`_num`／`_float`（market_snapshot、price_series）、`_num`（ETF
  daily_nav、monthly_stats）、`_to_int`（TAIFEX）、`to_int`（institutional）、`to_number`（sitca），以及 3 處寫在程式裡的
  轉換（外資持股比率、月營收、TDCC）。只新增 `float_or_none`；沒有數字一律 `None`，要當 0 的地方由呼叫端寫
  `or 0`（不另設 `int_or_zero`）。真實資料 16,436 個值新舊解析逐一相同，受影響工具 24 個案例輸出與 main 相同。
- ✅ `TradingDate` 取代日期驗證（#126）。做成參數型別而不是 Value Object：`toolkit.TradingDate`／`RequiredTradingDate`
  （西元 YYYYMMDD 的 pattern ＋ 日期必須存在），所有 56 個日期參數都用它，FastMCP 在工具執行前驗證，中文訊息由
  `ArgumentErrorsInChinese` 產生。刪掉 11 個模組的手寫檢查與 `parse_date_range` 的格式分支（`example` 參數一併拿掉）。
  字串原樣交給工具，轉成上游格式集中在 `utils.date_helper`：`roc_date`（`115/09/30`；`sep=""` → `1150930`）、
  `roc_year_of`、`slash_date`（TPEx `2026/09/30`），取代各處手寫的 `- 1911` 與切字串。驗證：56 個日期參數逐一
  實際呼叫，攔下 main 與分支送出的 93 個上游請求逐筆比對，全部相同。`Page` 取代手刻分頁已在 #115 完成。
- ✅ 參數西元、回覆民國的落差寫清楚（#127）：回覆沿用來源的民國日期（至少 27 支自訂工具與大多數 OpenAPI 透傳
  欄位），不改輸出；改用 server `instructions` 說明慣例與換算、60 個日期／月份參數說明標明「西元」、把民國樣式的
  輸入在錯誤訊息裡直接換算成西元。
- ✅ 列舉參數改 `Literal`、範圍改 `Field`（#125）：23 個列舉、所有 `limit`／`offset`（`toolkit.Limit`／`Offset`）
  與 `months`／`weeks`／`limit` 上限（`toolkit.bounded`）；刪掉 19 個模組裡的手寫檢查與 `check_choice`。
  FastMCP 依 schema 擋下錯誤值，回的是 pydantic 英文訊息；`toolkit.validation.ArgumentErrorsInChinese`
  middleware 把它改寫成中文（「sort_by 只能是 total、foreign、trust、dealer（收到 'x'）」）。日期格式、
  產業代碼這類開放集合、跨參數規則仍在函式內 `raise ToolError`。
- ✅ 統一 profitability 分頁寫法（#115）。
- 參數說明寫在 docstring 的 `Args:`：FastMCP 4 會搬進各參數的 `description`；`Returns:` 等其他段落會被丟掉，
  回傳內容寫在 `Args:` 之前（`回傳：…`，#107 已改，`test_tool_docstrings_unit.py` 把關）。
- 驗收：grep 計數 9→1、13→1、13→0。

### Phase 3：來源層 + 領域層（Strangler Fig，一端點一 PR）
- 順序：先做被重複解析的 STOCK_DAY、MI_INDEX、TWT49U、BWIBBU_d；再做 T86 + TPEx（Adapter 示範）；其餘逐步。
- contract test 改測 gateway：真實回應要能建出 dataclass（比「欄位存在」強，型別／單位變了也抓得到）。
- 105 個 OpenAPI 透傳 tool 不動，`create_company_tool` 已是對的抽象。
- 驗收：`r[n]` 只出現在 `sources/`，tools/ 內 0 處。

### Phase 4：MCP 介面（全部用 FastMCP 4 原生機制）
- ✅ 全部 tool 加 annotations 與依來源的 `tags`（#129）：`ToolRegistrar` 統一加上 `READ_ONLY`（唯讀、非破壞、
  冪等、open world；MCP SDK v2 欄位名 `read_only_hint` …）與模組的來源 tags（`tools.SOURCE_TAGS`，最長前綴：
  `twse` 131、`tpex` 17、`taifex` 17、`mops` 11、`sitca` 3、`ndc` 2、`cbc` 1、`tdcc` 1 支），`create_company_tool` /
  `create_list_tool` 產生的工具也經過它。新模組沒登記來源就註冊失敗；靜態檢查「碰到哪個網站就要有那個 tag」；
  用真實請求核對 59 支工具連到的網站都在 tags 內。
- ✅ 讓使用者只載入需要的子集（#130）：`TWSE_INCLUDE_SOURCES`／`TWSE_EXCLUDE_SOURCES`（逗號分隔的來源 tag）
  只決定開哪些來源，過濾本身是 FastMCP 的 `Visibility`（`tools.show_only_sources` 呼叫 `mcp.disable(tags=)`）。
  - 工具：讀到任何一個沒開的來源就隱藏（`get_etf_info` 要 sitca＋twse＋tpex 都開），呼叫時是 `Unknown tool`。
  - prompt：多數 prompt 跨 4–6 個來源，全部要開才顯示太嚴；改成只要有一個來源開著就保留（再加一個只對
    prompt 的 `mcp.enable(tags=開著的來源)`，後加的標記優先）。prompt 的 tags 是它點名的工具的來源聯集，
    測試把兩邊綁在一起。
  - server instructions 開頭只列開著的來源（`tools.SOURCES` 改存簡稱，預設輸出與之前逐字相同）。
  - 打錯來源名稱、或全部排除，server 直接啟動失敗，不默默藏掉工具。
- 177 個 tool 吃 context：評估 `RegexSearchTransform`（`list_tools` 只剩 `search_tools` + `call_tool`，
  需要時再搜）。**不要用 `BM25SearchTransform`**：它的 tokenizer（`[^\W_]{2,}`）不切中文，整段中文描述
  變成一個詞，實測「外資 買超 排行 上市」排第一的是期貨月統計；regex `外資.*買超` 則正確找到三支三大法人
  tool。要 BM25 就得自訂 `BaseSearchTransform`，用中文 bigram 斷詞。先確認主要 client 能好好用
  `call_tool` 代理再上線。
- 文字型 tool 設 `output_schema=None`，`tools/call` 不再把同一份文字在 `structuredContent` 多回一次；
  screener、技術指標這類改回真的結構化資料（dataclass → output schema）。
- ✅ `ResponseLimitingMiddleware` 當最後保險（#132）：`toolkit.response_limit` 換上中文截斷說明，`server.py` 預設
  500,000 bytes（`TWSE_MAX_RESPONSE_BYTES`，0 關閉）。實測：正常回應 2–48 KB、一次取整個市場 60–280 KB（上市全部
  1,383 檔 184 KB、TXO 全部履約價 280 KB），只有含權證的全量才到 1.7–5.6 MB（`get_warrant_basic_info(limit=100000)`
  44,717 筆、上櫃全部證券 12,950 筆、T86 `category="ALL"` 19,990 筆），上限只截這些。74 個 `limit` 參數沒有上限，
  各 tool 的筆數控制仍是另一件事（`Page(max_limit=)`）。截斷點落在位元組上，說明裡標明最後一行可能不完整。
- ✅ prompts 改自動發現（#131）：`prompts/` 每個模組一個公開函式，函式名稱＝prompt 名稱、docstring＝說明，
  `prompts.register_all_prompts` 逐一註冊，`server.py` 刪掉 9 個 wrapper。prompt 的來源 tags 不再手寫：
  `register_all_tools` 回傳每支工具的 tags，prompt 取它點名的工具（`` `get_xxx(...)` ``）的聯集；點名不存在的工具，
  server 啟動失敗。函式改成原本對外的名稱（`twse_stock_trend_prompt` → `stock_trend_analysis_prompt` 等），兩個說明
  改成 server.py 原本用的版本；prompts/list 與 20 組渲染結果和 main 逐字相同，只有清單順序變成模組名稱順序。

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
| `@mcp.tool` 新參數 | `annotations`、`tags`、`timeout`、`task`、`version`、`title`、`output_schema`、`run_in_thread` | Phase 1（task）、Phase 4（annotations/tags/output_schema） |
| `timeout=` 用在同步 tool | `anyio.fail_after` 取消不了 threadpool 裡的執行緒：等它做完才丟逾時錯誤（英文），結果作廢。實測 timeout=1 的 3 秒工具 3.2 秒才回 | 不用；時間上限用 `utils/deadline.time_budget`（#123） |
| `-> str` 的 outputSchema | 每個 tool 自動 `{"result": string}`，回應同一份文字兩次；`output_schema=None` 可關 | Phase 4 |
| 參數驗證 | 依 schema（`Literal`、`Field`）驗證，`additionalProperties: false`；docstring `Args:` → 參數說明。錯誤是 pydantic 英文；`on_call_tool` middleware 拿得到 `fastmcp.exceptions.ValidationError`（`__cause__.errors()` 是結構化資料），可統一改寫 | 已用（#125），中文改寫見 `toolkit/validation.py` |
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
   - 已加：per-site circuit breaker（#122）：連續失敗或被擋（403／429、MOPS 的 `FOR SECURITY REASONS`）就停打
     該網站一段冷卻時間，直接回錯誤。被擋時繼續打只會延長封鎖：2026-10-21 一個每 0.5 秒重打同一頁、
     持續數分鐘的腳本，讓證交所對 Python client 回非 JSON 好幾分鐘，停手後才自行恢復。
4. **連線重用**：已加，每網站一個 `requests.Session` 連線池（#113）。
5. **不做**：用代理池輪換 IP 規避封鎖，違反資料來源的使用條款。

## 不要做的事

- 一次重寫 177 個 tool：一端點一 PR，contract test 當安全網。
- 引入 DI 框架：`register_tools(mcp, client)` closure 注入已夠。
- 先全面 async（httpx）：FastMCP 4 已把同步 tool 放進 threadpool，改 async 沒有額外效益。
- 自己做 FastMCP 已有的東西：tool 過濾用 `Visibility`、輸出上限用 `ResponseLimitingMiddleware`。
  （例外：時間上限。`@mcp.tool(timeout=)` 擋不住同步 tool，所以用 `utils/deadline.time_budget`，見 Phase 1。）
- 為 pattern 而 pattern：透傳型 tool 就該是一行 factory。
