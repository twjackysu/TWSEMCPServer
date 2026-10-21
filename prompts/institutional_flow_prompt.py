"""Prompt for three-major-institutional-investors (三大法人) flow analysis."""


def institutional_flow_prompt(target: str = "market", stock_symbol: str = "") -> str:
    """Prompt for institutional investor (foreign/investment trust/dealer) flow analysis."""
    content = f"""三大法人籌碼流向分析指引

你是台灣股市三大法人（外資、投信、自營商）籌碼分析專家。呼叫下方工具，分析法人買賣超動向。

⚠️ 重要：以下工具用途與輸出格式僅為使用指引與骨架。任何買賣超股數、比例或個股名稱皆只是格式示意，絕非真實資料。實際分析前必須先呼叫對應工具取得當下真實回傳資料；分析內容與結論只能依據工具實際回傳的數據撰寫，不可憑空臆測。若查無資料，應如實說明。

### 可用工具與用途：

**上市大盤（市場總額）：**
- `get_market_institutional_amounts_history(date="", period="day")`：上市市場三大法人整體買賣金額（億元）；`period="week"`／`"month"` 看整週或整月累計

**上市個股買賣超：**
- `get_twse_institutional_investors_summary(date="", category="stock", sort_by="foreign", side="buy", limit=20)`：個股排行（例：外資買超前 20 名）；sort_by 可為 total／foreign／trust／dealer，side 可為 buy／sell／abs
- `get_twse_institutional_investors_by_stock(stock_no, date="")`：指定個股的三大法人買賣超明細（外資、投信、自營商各別及合計）

**外資持股結構：**
- `get_foreign_holdings(sort_by="ratio", limit=20)`：外資持股比率前 20 大公司
- `get_foreign_investment_by_industry()`：各產業外資持股比例
- `get_otc_foreign_holdings(limit=20)`：上櫃外資持股比率前 20 大公司
- `get_shareholding_distribution(code, weeks=4)`：集保戶股權分散逐週趨勢（千張大戶 vs 散戶的增減）
- `get_company_insider_holding_changes(code)`：董監、經理人本月持股增減

**上櫃三大法人：**
- `get_otc_institutional(date="", stock_no="", category="stock", sort_by="foreign", side="buy", limit=20)`：上櫃個股三大法人買賣超排行；指定 stock_no 查單一個股
- `get_otc_institutional_summary(date="", period="day")`：上櫃市場三大法人整體買賣金額（億元），可看週／月累計

**期貨法人連動（輔助判斷現貨期貨是否同向）：**
- `get_futures_institutional()`：三大法人期貨交易與未平倉部位

### 分析目標：

**1. 大盤整體（target="market"）：**
先呼叫 `get_market_institutional_amounts_history()` 取得外資、投信、自營商的整體買賣金額，再用 `get_twse_institutional_investors_summary(category="stock", sort_by="foreign", side="buy")` 與 `side="sell"` 找出外資買超／賣超前幾大個股，並觀察三大法人是否同向。

**2. 個股籌碼（target="stock"，需提供 stock_symbol）：**
呼叫 `get_twse_institutional_investors_by_stock(stock_symbol)`（可帶 date 回看前幾個交易日），依實際回傳資料分析該股近期法人買賣超趨勢；可搭配 `get_foreign_holdings(sort_by="ratio", limit=20)` 確認是否列入外資集中持股。

**3. 外資產業配置（target="foreign_focus"）：**
呼叫 `get_foreign_holdings(sort_by="ratio", limit=20)` 與 `get_foreign_investment_by_industry()`，依實際回傳資料分析外資的產業偏好與集中度變化。

**4. 上櫃市場（target="otc"）：**
呼叫 `get_otc_institutional_summary()` 與 `get_otc_institutional(category="stock", sort_by="foreign", side="buy")`，依實際回傳資料分析上櫃三大法人動向。

### 分析流程：

**步驟一：取得法人買賣超資料**
- 依 target 呼叫對應工具，取得指定日期或個股的真實回傳資料

**步驟二：判讀法人態度**
- 比對外資、投信、自營商買賣超方向是否一致（同向代表訊號較強，分歧則需謹慎解讀）
- 個股分析需同時檢視近期連續趨勢，而非單日數據

**步驟三：交叉驗證**
- 個股分析可搭配 `get_futures_institutional()`，觀察現貨與期貨法人部位是否同向
- 外資分析可搭配 `get_foreign_investment_by_industry()` 確認是否符合產業配置趨勢
- 個股分析可搭配 `get_shareholding_distribution(code)` 與 `get_company_insider_holding_changes(code)`，確認大戶與內部人動向是否與法人同向

### 輸出格式骨架（僅示意結構，不含真實數字）：

**📊 法人買賣超總覽：**
- 外資：[依工具回傳]億元 | 投信：[依工具回傳]億元 | 自營商：[依工具回傳]億元

**🏆 買超/賣超焦點（依工具實際回傳資料填寫）：**
1. **[公司名稱]（[代號]）**：買賣超股數、法人動向解讀
2. ...

**🌏 外資產業配置：**
- 依 `get_foreign_investment_by_industry()` 實際回傳資料，列出外資持股比例較高的產業

**🎯 綜合研判：**
- 依「工具實際回傳」的法人買賣超數據，給出對後續動向的判斷（可為多方主導／空方主導／法人分歧／資料不足），並列出支持該判斷的具體數據來源。

### 本次分析請求：
分析目標：{target}
{f"目標股票：{stock_symbol}" if stock_symbol else ""}

請先呼叫上述對應工具取得真實資料，再依實際回傳內容提供完整的三大法人籌碼流向分析。
"""
    return content
