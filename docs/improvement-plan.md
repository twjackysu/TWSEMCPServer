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
   - ✅ TPEx tradingStock（#137）：`sources/tpex/trading_stock.py`；`get_otc_stock_history` 與 `price_series`
     的上櫃日K共用。成交量欄名 2025-01 起是「成交張數」、之前（查到 2005）是「成交仟股」，數字相同，gateway
     兩個都接受（只看第一個的話 2024-12 以前會變成查詢失敗）。tool 改查當月 1 日（整月資料相同），並與
     `price_series` 共用月份快取。12 組呼叫（含 2010、2024-12／2025-01 跨欄名、還原日K、技術指標）文字與
     結構化資料都與 main 逐字相同。
   - ✅ TPEx exDailyQ（#138）：`sources/tpex/ex_daily_q.py`；`get_otc_exright` 與上櫃還原權息共用，`price_series`
     兩個市場的除權息事件改成同一段（兩個 gateway 的欄位名稱相同）。修好一個依位置讀造成的錯：區間起點在 2016 年
     以前時，回應每一列都多一欄「員工紅利轉增資」（在現金增資股數之前），舊版把它當成現增股數，幾乎每列都多印
     「現增:0.00股@…」或「現增:2369.00股@0」。17 組呼叫中 15 組文字與 main 逐字相同，另 2 組（2008-12、
     2015-12～2016-01）只差在現增那一段。數字沒有千分位、最多 8 位小數，輸出用 `f"{d:f}"`（`str(Decimal("0.00000000"))`
     是 `0E-8`）。
   - 盤點（2026-10-22，只看不改）：還在依位置讀、可查過去日期的 36 個端點（TWSE rwd 12、TPEx 網站 5、TAIFEX 下載 10、
     MOPS 9），各抽 2005、2010、2014、2015、2018、2021、2025 與最新一天，用工具實際呼叫並錄下回應比對欄位。TAIFEX、MOPS
     都沒變過（TAIFEX 三大法人 5 個下載頁只保留約 3 年）。有變、而且工具會出錯的：
     | 端點（工具） | 改變 | 舊版 |
     |---|---|---|
     | TPEx afterTrading/otc（`get_otc_daily` 帶日期） | 2020-04-30 起多最後買量／賣量 | 最後賣價印成發行股數（#139 修好） |
     | TWSE TWT93U（融券借券餘額） | 2012-03-19 起借券 5 欄改 6 欄 | 借券的還券、調整、餘額、限額整排錯位（#140 修好） |
     | TPEx peQryDate（`get_otc_valuation` 帶日期） | 2025-01-02 起多「財報年/季」 | 2025 年以前一律查詢失敗（#141 修好） |
     | TWSE BFIAUU（鉅額交易明細） | 2011-12-19 起拿掉「交割期別」 | 2011-12-16 以前查詢失敗（#142 修好） |
     | TPEx insti/summary（上櫃法人買賣金額） | 欄位沒變，有些日子多一列 `[]` | 那些日子查詢失敗（#143 修好） |

     變了但讀的欄位不受影響：MI_QFIIS（2005 年少一欄陸資上限，在工具讀的欄位之後）、TAIFEX optDataDown（2026 年最後
     多「契約到期日」）、BFI82U（2014 年底自營商拆兩列，列名照印）。afterTrading/otc 與 peQryDate 其實也被
     `services/market_snapshot` 解析（選股、同業比較），之前以網址字串搜尋時漏掉，所以 #138 時並不是「多處解析的
     都做完了」。順序：先修會印錯數字的，再修會失敗的，最後是沒變過的。
   - ✅ TPEx afterTrading/otc（#139）：`sources/tpex/daily_quotes.py`；`get_otc_daily`（帶日期）與 `market_snapshot`
     （最新一日上櫃行情、產業成員）共用。依欄名讀，修好 2020-04-29 以前「最後買/賣」的賣價印成發行股數（例如
     `7.97/247,000,000` → `7.97/8.00`）。價格沒有成交是 `----`、2018 年以前超過千元的價格沒有千分位，工具以
     `printed(value, blank="----")` 輸出。19 組呼叫：2020-04-30 起的整天行情、選股、同業比較（含結構化資料）與 main
     逐字相同；2020-04-29 以前每列只差最後賣價，另 2015-01-05 有 1 列千元以上的價格多了千分位。
   - ✅ TWSE TWT93U（#140）：`sources/twse/twt93u.py`；`get_short_sale_lending_balance_history` 改走 gateway。融券、借券兩組
     都有「前日餘額」，所以欄位用回應的 `groups` 組成「組名/欄名」來找（例如「借券賣出/前日餘額」）。2012-03-19 證交所
     改用新公式後，借券是前日／當日賣出／當日還券／當日調整／當日餘額／次一營業日可限額；之前是前日／賣出／庫存異動
     （帶正負號）／今日餘額／可使用額度，舊版依位置讀，把可使用額度印成當日餘額、備註印成次日可限額。兩種格式的數字
     意義不同，舊日期照證交所當時的欄名輸出，工具說明也註明。合計列由 gateway 去掉。15 組呼叫：2012-03-19 起的整天
     輸出與 main 逐字相同，2012-03-16 以前只差借券那一行。
   - ✅ TPEx peQryDate（#141）：`sources/tpex/pe_qry_date.py`；`get_otc_valuation` 與 `market_snapshot`（上櫃估值）共用。
     依欄名讀，「財報年/季」（2025-01-02 起才有）沒有時是空字串，工具就不印「（財報 …）」，2010–2024 的日期從查詢失敗
     變成有資料。數字沒有千分位（本益比 `11125.00`）、缺值是 `N/A`、每股股利 8 位小數，工具以 `f"{d:f}"` 輸出、None 印 `N/A`。
     18 組呼叫：2025-01-02 起的整天估值、選股 3 組、同業比較 2 組（含結構化資料）與 main 逐字相同。
   - ✅ TWSE BFIAUU（#142）：`sources/twse/bfiauu.py`；`get_block_trades_detail` 改走 gateway，依欄名讀、總計列由 gateway
     去掉。2011-12-16 以前多一欄「交割期別」，舊版解成 6 個值時失敗；現在這些日期有資料，交割期別接在交易別後面
     （「配對交易 T+2日交割」）。14 組呼叫：2011-12-19 起與 main 逐字相同。
   - ✅ TPEx insti/summary（#143）：`sources/tpex/insti_summary.py`；`get_otc_institutional_summary` 改走 gateway，依欄名讀，
     空列 `[]` 略過（2018-01-02 的日報、週報在 4 列之後多一列空的，舊版解成 4 個值時失敗；那兩天上游本身沒有外資的列）。
     13 組呼叫中 11 組與 main 逐字相同，另 2 組是 2018-01-02 從查詢失敗變成有資料。盤點表上的格式問題至此都已修好。
   - contract test 只留介面（#144）：#137–#143 的 contract test 混進了替上游驗資料的檢查（餘額等式、金額加總、
     成交價×股數、參考價公式、數值範圍、單位推算、高低價順序），#116、#118、#121 的也有幾項（每列都有成交、除息日與
     種類、舊日期一定是舊格式）。全部拿掉，每個 gateway 只留：固定歷史日的真實回應能建出 dataclass（欄位改名就失敗）、
     舊格式那天也能讀、一列固定探測列的數字能解析（格式變了工具會印成 `--`）、工具依賴的參數行為與標籤（type=EW、
     prod、區間長度、末列的「合計／總計」）。欄位讀錯靠 gateway 依欄名取值與單元測試的錄製回應把關。
     #145 再把這條規則交給 CI：`tests/unit/test_contract_scope_unit.py` 擋 contract test 裡的算術、大小比較與
     abs／sum 等（例外要寫 `# contract-ok: <理由>`）。
   - ✅ TAIFEX futDataDown／optDataDown（#146）：建立期交所下載頁的 gateway 寫法——`sources/taifex/download.py`
     的 `download_table()` 送表單、解 cp950 CSV、依標題名稱找欄，`number()`／`count()` 轉數字（CSV 沒有千分位、
     沒值是 `-`）；`sources/taifex/daily_report.py` 的 `futures_quotes()`／`option_quotes()` 回 `FuturesQuote`／
     `OptionQuote`，`has_regular_session()` 用於最新交易日往回找。`utils.taifex.fetch_period` 改成泛型，可直接收
     gateway 的結果。兩支每日行情工具 19 組呼叫（最新一日、2005／2010／2018 整月、股票期貨、各種篩選）與 main
     逐字相同。
   - ✅ 其餘 TAIFEX 下載頁（#147）：三大法人 5 頁（`sources/taifex/institutional.py`：總表、期貨／選擇權分計、
     各期貨契約、各選擇權契約、買賣權分計，共用 12 欄的 `Positions`）、大額交易人 2 頁（`large_traders.py`）、
     PCR（`put_call_ratio.py`）都依標題名稱讀。數字輸出改用共用的 `utils.plain()`（原樣小數、沒值印 `-`）。
     39 組呼叫（最新一日、2005–2026 的單日與整月、契約代碼／中文名稱／買賣權篩選、列出契約、超出保存期限、
     非交易日、區間錯誤）與 main 逐字相同，送出的請求也相同。工具讀的期交所下載頁全部收成 gateway（tick zip 除外）。
   - ✅ MOPS ajax_t35sc09（#148）：`sources/mops/t35sc09.py` 的 `treasury_buybacks()` 回 `Buyback`。舊版 HTML 的表頭跨兩列
     （買回價格區間、預定買回期間各分兩欄），去掉 `<br>` 與紅字註記後，把兩列表頭接成「買回價格區間/最低」再依欄名取值；
     資料列寬度不符就報錯（舊版會默默略過）。2005–2026 上市、上櫃、公開發行都是同樣 20 欄。沒有案件時頁面是
     「查無所需資料」（gateway 回 None），沒有表格又沒這句話時報錯。17 組呼叫（2005／2008／2010 上櫃／2015／2020／
     2025 三個市場、分頁、代號篩選、查無）與 main 逐字相同，送出的請求也相同。背書保證頁（t05st11）把表格原樣印出，
     沒有依位置讀，不需要 gateway。
- [x] Phase 2 共用核心（#125 Literal／Field、#126 TradingDate、#127 日期慣例、#128 數字解析）
- [ ] Phase 3 來源層 + 領域層（進行中：#116–#119、#121、#137–#143、#146–#148；盤點出的格式問題都已修好，剩格式沒變過、
  只在一處依位置讀的端點：MOPS 其餘頁面、TWSE rwd、TPEx 網站）
- [x] Phase 4 MCP 介面（#109 output_schema、#127 server instructions、#129 annotations／tags、
  #130 依來源開關工具、#131 prompts 自動註冊、#132 回應大小上限、#133 結構化輸出、#134 工具搜尋用詞與順序；
  搜尋式工具清單評估後不採用，改由 client 端的 tool search 處理）
- [x] Phase 5 打包（#135 Dockerfile 多階段／non-root／HEALTHCHECK、移除 requirements 與未用依賴，#136 pyright）

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
    `httpx`、`mcp[cli]` 宣告但未直接用；無 ruff / pyright。（已修：#124 ruff、#135 Dockerfile 與依賴、#136 pyright）
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
  與 `months`／`weeks`／`limit` 上限（`toolkit.bounded`；#136 起改成直接寫 `Annotated[int, Field(ge=, le=)]`，
  型別標註裡的函式呼叫 pyright 不接受）；刪掉 19 個模組裡的手寫檢查與 `check_choice`。
  FastMCP 依 schema 擋下錯誤值，回的是 pydantic 英文訊息；`toolkit.validation.ArgumentErrorsInChinese`
  middleware 把它改寫成中文（「sort_by 只能是 total、foreign、trust、dealer（收到 'x'）」）。日期格式、
  產業代碼這類開放集合、跨參數規則仍在函式內 `raise ToolError`。
- ✅ 統一 profitability 分頁寫法（#115）。
- 參數說明寫在 docstring 的 `Args:`：FastMCP 4 會搬進各參數的 `description`；`Returns:` 等其他段落會被丟掉，
  回傳內容寫在 `Args:` 之前（`回傳：…`，#107 已改，`test_tool_docstrings_unit.py` 把關）。
- 驗收：grep 計數 9→1、13→1、13→0。

### Phase 3：來源層 + 領域層（Strangler Fig，一端點一 PR）
- 順序：先做被重複解析的 STOCK_DAY、MI_INDEX、TWT49U、BWIBBU_d；再做 T86 + TPEx（Adapter 示範）；其餘逐步。
- contract test 改測 gateway：真實回應要能建出 dataclass（比「欄位存在」強，數字格式變了也抓得到）。只驗介面：
  不檢查上游資料本身對不對（加總、等式、範圍、單位），那是資料來源自己的事。
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
- ✅ 177 個 tool 吃 context：評估 `RegexSearchTransform`（`list_tools` 只剩 `search_tools` + `call_tool`，
  需要時再搜）後**不採用**，改由 client 端搜尋（2026-10-22）。**不要用 `BM25SearchTransform`**：它的 tokenizer
  （`[^\W_]{2,}`）不切中文，整段中文描述變成一個詞，實測「外資 買超 排行 上市」排第一的是期貨月統計。
  - 主要 client 是 JackyAIApp（Anthropic Messages API + MCP connector + Haiku 5.5，連 Horizon 上的公開 server）。
    Anthropic API 本身就有 tool search，以 8 題中文問題、和 JackyAIApp 相同的請求參數實測：
    | 設定 | 正確 | 每題 context tokens | 每題費用 |
    |---|---|---|---|
    | 全部 177 支載入（現況） | 8/8 | ~133K（工具定義每次模型呼叫 ~53K） | $0.0088 |
    | API `tool_search_tool_regex_20251119` + `mcp_toolset.default_config.defer_loading`，5 支常用不延遲、system prompt 一句提示 | 8/8 | ~21K | $0.0018 |
    | 同上但不釘選、不提示 | 8/8，一次沒產出答案 | ~26K | $0.0028 |
    | API `tool_search_tool_bm25_20251119` | 6/8（中文查詢多半搜不到） | ~28K | $0.0033 |

    tool search 不另外計費。JackyAIApp 的修改由該 repo 處理。
  - server 端的 transform 不採用的原因：公開 server 的 tools/list 會對所有使用者變成兩支工具；`search_tools`／
    `call_tool` 沒有 annotations，177 支工具的唯讀標記對 client 消失，Claude Code 允許一次 `call_tool` 就放行全部；
    多一層代理呼叫，搜尋結果是 JSON 文字而不是原生工具定義；regex 只取前 5 筆、不排序（離線「成分股|持股」就漏掉
    `get_etf_holdings`）；Claude Code 本身也會延遲載入 MCP 工具，等於搜兩次。經 `call_tool` 的呼叫仍受 #132 的大小
    上限與 #130 的來源過濾約束，若日後有不支援 tool search 的 client，可再做成預設關閉的選項。
- ✅ 讓 client 端的搜尋找得到（#134）：Anthropic 的 regex tool search 在名稱、描述、參數名稱與說明裡 `re.search`，
  **依 tools/list 順序**取前 5 筆（或模型給的 `limit`，多半是 10），不排序——實測的結果順序與 tools/list 完全一致。
  所以一支工具找不找得到，取決於它的文字有沒有那個詞、以及前面有沒有一堆也匹配的工具。
  - 用詞：補上使用者常講、而資料確實有的說法（PCR／賣買權比、台指期、分K、K線／歷史股價、選股、YoY、每股盈餘、
    股東權益、自由現金流、質押、填息、量能、休市、公司資料…，22 個檔案 26 處）。常用工具的 242 個用詞中，描述裡
    找不到的從 38 個降到 1（「日程」：資料寫的是日期，不補）。
  - 順序：TWSE OpenAPI 轉發的 package（broker、company、market、other、trading，105 支，用詞籠統：持股、股利、
    公司、指數）改排在手寫的工具之後（`tools.OPENAPI_PACKAGES`）。
  - 離線模擬（`tests/unit/test_tool_search_unit.py`）：單一用詞搜尋時正確工具在前 10 名 200/242 → 234/242
    （前 5 名 181 → 216）；實測中模型寫的寬鬆 pattern 前 5 名 12/20 → 15/20。測試守住：用詞都在工具文字裡、
    50 個常見問法在前 10 名內、OpenAPI 轉發工具排最後。
- ✅ 文字型 tool 設 `output_schema=None`（#109），`tools/call` 不再把同一份文字在 `structuredContent` 多回一次；
  ✅ screener、技術指標這類改回真的結構化資料（#133）：`tools/analytics` 4 支（選股、同業比較、還原日K、技術指標）
  `output_schema(Result)` ＋ `structured_reply(text, result)`（`toolkit/structured.py`）。
  - `content` 仍是原本的文字，不改成 JSON：LLM client 讀的是 content，中文排版（「收盤高於 MA20」、名次
    80/168）比英文欄位的 JSON 好讀也省 token。MCP 對這點只是 SHOULD（content 附上序列化的 JSON）。
  - 文字由 dataclass 產生，兩邊不會不一致；欄位全部附說明（單位、西元／民國），由測試把關。
  - 宣告了 schema，成功回覆就必須附結構化資料（client 會驗證），所以這 4 支的「查無」改成 `ToolError`
    （`isError` 由 false 變 true，文字不變）。
  - `ResponseLimitingMiddleware` 會把它限制的工具的 output schema 從 tools/list 拿掉，所以只套用到文字工具
    （`RegisteredTools.text_tools`）；結構化工具自己限制大小：選股、同業比較的 `limit` 上限 500。
  - 實測 17 組呼叫：文字與 main 逐字相同，結構化資料逐列對得上文字，client 端 schema 驗證全過。
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
- ✅ Dockerfile 多階段、non-root、去 Node.js、`--no-dev`、HEALTHCHECK（#135）：builder 用固定版本的 uv
  （`ghcr.io/astral-sh/uv:0.7.12`）把 `uv.lock` 的執行期依賴裝進 `/app/.venv`（`--frozen --no-dev`）；執行映像檔只有
  venv 與各 package，沒有 uv、Node.js、`staticFiles`，以 `app`（uid 10001）執行，程式碼屬於 root、唯讀。
  `server.py` 新增 `GET /health`（不碰上游，來源掛掉不會讓容器變 unhealthy）；HEALTHCHECK 在 HTTP 模式打它，
  stdio 模式（`MCP_STDIO=1`）沒有 port 可測，直接回健康。實測（Docker 29.9.2）：映像檔 494 MB → 211 MB；
  uid 0 → 10001；node／npm／uv／curl 都不在了；stdio 列出的工具／prompts／instructions 與本機逐字相同、實際
  呼叫成功；HTTP 的 `/health` 回 `ok`，HEALTHCHECK 在 HTTP 與 stdio 模式都是 healthy。
- ✅ 移除 `requirements*.txt` 與未用依賴（#135）：`httpx`（沒有任何 import）、`mcp[cli]` 的 cli extra（typer 等；
  `mcp` 本身保留，#129 起直接用 `mcp.types`）、dev 的 `pytest-mock`、`pytest-asyncio`（沒用到）；`server.py`
  直接 import 的 `starlette` 補宣告。`uv.lock` 只少了 7 個套件，其他版本不變。`requirements.txt` 原本可能是
  Horizon 的依賴來源，刪除後 Horizon 改讀 `pyproject.toml`（直接依賴的版本照舊，下游套件不再鎖定；使用者決定）。
- ✅ pyright basic 模式（#136）：`uv run pyright`（dev extra 固定 `pyright==1.1.414`，設定在 `[tool.pyright]`），
  檢查 server 的 7 個 package，不含 `tests/`；Unit Tests workflow 在 ruff 之後跑。起始 118 個錯誤、2 個警告 → 0。
  沒有找到執行期 bug：都是型別寫法跟不上程式本身的保證，全部改成行為不變的寫法，tools/list、prompts、instructions
  與 main 逐字相同。
  - 79 個是 `TWSEDataItem`：原本是列了 60 個固定欄位的 `TypedDict`，但 OpenAPI 每個端點欄位都不同，改成
    `Dict[str, Any]`；`DataFormatter` 的參數改 positional-only，`format_list_response` 依資料型別泛型化。
  - 9 個是 `bounded(1, MAX_ROWS)`：型別標註裡的函式呼叫不是合法型別，改成直接寫 `Annotated[int, Field(ge=, le=)]`
    （schema 不變），刪掉 `toolkit.bounded`。
  - 「(結果, None) 或 (None, 錯誤)」的平行 Optional tuple（`utils.taifex.parse_date_range`、MOPS
    `parse_month_range`）改成回傳 `Union[結果, str]`，呼叫端 `isinstance(x, str)` 判斷。
  - 其餘是 Optional 收窄：在原本就保證有值的地方明寫 `is not None`（與原本的真假判斷同義），或以 `cast` 註明
    保證來自哪裡（技術指標前已濾掉缺高低收的日子、MACD 的 DIF 從第一個有值的日子起都有值）。

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
| Search transform | `RegexSearchTransform` 中文可用；`BM25SearchTransform` 不切中文 | 評估後不採用（client 端用 Anthropic tool search，#134） |
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
