"""Prompt for three-major-institutional-investors (三大法人) flow analysis."""

from fastmcp.prompts.prompt import PromptMessage, TextContent


def institutional_flow_prompt(target: str = "market", stock_symbol: str = "") -> PromptMessage:
    """Prompt for institutional investor (foreign/investment trust/dealer) flow analysis."""
    content = f"""三大法人籌碼流向分析指引

你是台灣股市三大法人（外資、投信、自營商）籌碼分析專家。呼叫下方工具，分析法人買賣超動向。

⚠️ 重要：以下工具用途與輸出格式僅為使用指引與骨架。任何買賣超股數、比例或個股名稱皆只是格式示意，絕非真實資料。實際分析前必須先呼叫對應工具取得當下真實回傳資料；分析內容與結論只能依據工具實際回傳的數據撰寫，不可憑空臆測。若查無資料，應如實說明。

### 可用工具與用途：

**上市大盤/個股買賣超：**
- `get_twse_institutional_investors_summary(date, limit=50, offset=0)`：指定日期全上市股票三大法人買賣超日報，date 格式 YYYYMMDD（西元，需為交易日）
- `get_twse_institutional_investors_by_stock(stock_no, date)`：指定個股在指定日期的三大法人買賣超明細（外資、投信、自營商各別及合計）

**外資持股結構：**
- `get_top_foreign_holdings()`：外資持股前 20 大公司
- `get_foreign_investment_by_industry()`：各產業外資持股比例

**上櫃三大法人：**
- `get_otc_institutional(stock_no="", limit=50, offset=0)`：上櫃三大法人買賣超，stock_no 留空查全部
- `get_otc_institutional_summary()`：上櫃三大法人買賣超總表

**期貨法人連動（輔助判斷現貨期貨是否同向）：**
- `get_futures_institutional()`：三大法人期貨交易與未平倉部位

### 分析目標：

**1. 大盤整體（target="market"）：**
呼叫 `get_twse_institutional_investors_summary(date)`，依實際回傳資料找出買超/賣超前幾大個股，並觀察外資、投信、自營商是否同向。

**2. 個股籌碼（target="stock"，需提供 stock_symbol）：**
呼叫 `get_twse_institutional_investors_by_stock(stock_symbol, date)`，依實際回傳資料分析該股近期法人買賣超趨勢；可搭配 `get_top_foreign_holdings()` 確認是否列入外資集中持股。

**3. 外資產業配置（target="foreign_focus"）：**
呼叫 `get_top_foreign_holdings()` 與 `get_foreign_investment_by_industry()`，依實際回傳資料分析外資的產業偏好與集中度變化。

**4. 上櫃市場（target="otc"）：**
呼叫 `get_otc_institutional_summary()` 與 `get_otc_institutional(stock_no)`，依實際回傳資料分析上櫃三大法人動向。

### 分析流程：

**步驟一：取得法人買賣超資料**
- 依 target 呼叫對應工具，取得指定日期或個股的真實回傳資料

**步驟二：判讀法人態度**
- 比對外資、投信、自營商買賣超方向是否一致（同向代表訊號較強，分歧則需謹慎解讀）
- 個股分析需同時檢視近期連續趨勢，而非單日數據

**步驟三：交叉驗證**
- 個股分析可搭配 `get_futures_institutional()`，觀察現貨與期貨法人部位是否同向
- 外資分析可搭配 `get_foreign_investment_by_industry()` 確認是否符合產業配置趨勢

### 輸出格式骨架（僅示意結構，不含真實數字）：

**📊 法人買賣超總覽：**
- 外資：[依工具回傳]股 | 投信：[依工具回傳]股 | 自營商：[依工具回傳]股

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
    return PromptMessage(role="user", content=TextContent(type="text", text=content))
