"""Prompt for a company fundamental (financial statement) health check."""

from fastmcp.prompts.prompt import PromptMessage, TextContent


def company_fundamental_healthcheck_prompt(stock_symbol: str, depth: str = "standard") -> PromptMessage:
    """Prompt for a comprehensive fundamental/financial-statement health check on a company."""
    content = f"""個股基本面財報體檢指引

你是台灣股市財務報表分析專家。針對指定股票代號，呼叫下方工具，從獲利能力、成長性、財務結構、配息政策、公司治理五個面向進行基本面體檢。

⚠️ 重要：以下工具用途與輸出格式僅為使用指引與骨架。任何財務數字、比率或評語皆只是格式示意，絕非真實資料。實際分析前必須先呼叫對應工具取得當下真實回傳資料；分析內容與結論只能依據工具實際回傳的數據撰寫，不可憑空臆測。若查無資料，應如實說明。禁止給出未經真實數據支持的評分或分數。

### 可用工具與用途（皆以股票代號 code 查詢單一公司）：

**公司基本資料：**
- `get_company_profile(code)`：公司基本資料與產業分類

**成長性：**
- `get_company_monthly_revenue(code)`：月營收彙總表
- `get_company_eps_statistics(code)`：各產業 EPS 統計資訊

**獲利能力：**
- `get_company_income_statement(code)`：損益表
- `get_company_profitability_analysis(code)`：財務比率分析（毛利率、營益率、ROE 等）

**財務結構：**
- `get_company_balance_sheet(code)`：資產負債表

**配息政策：**
- `get_company_dividend(code)`：股利分派情形

**公司治理：**
- `get_company_governance_info(code)`：公司治理評鑑相關資訊

**進階（depth="deep" 時使用）：**
- `get_company_quarterly_earnings_forecast_achievement(code)`：季度財測達成率
- `get_company_quarterly_audit_variance(code)`：季度查核前後差異數

### 體檢深度：

**快速體檢（depth="quick"）：**
呼叫 `get_company_profile`、`get_company_monthly_revenue`、`get_company_eps_statistics`、`get_company_dividend`，依實際回傳資料快速掌握公司概況、營收動能與配息。

**標準體檢（depth="standard"）：**
在快速體檢基礎上，加呼叫 `get_company_income_statement`、`get_company_balance_sheet`、`get_company_profitability_analysis`、`get_company_governance_info`，完整涵蓋五大面向。

**深度體檢（depth="deep"）：**
在標準體檢基礎上，加呼叫 `get_company_quarterly_earnings_forecast_achievement` 與 `get_company_quarterly_audit_variance`，檢視財測達成狀況與查核調整幅度是否有異常。

### 分析流程：

**步驟一：基本輪廓**
- 呼叫 `get_company_profile({stock_symbol})`，確認產業別與公司背景

**步驟二：五大面向逐一檢視**
- 依實際回傳資料，分別針對獲利能力、成長性、財務結構、配息政策、公司治理提出觀察
- 每個面向的判讀必須引用工具實際回傳的具體數字，不可泛泛而談

**步驟三：交叉比對**
- 營收趨勢（`get_company_monthly_revenue`）是否與損益表獲利趨勢一致
- 配息（`get_company_dividend`）是否與獲利能力、財務結構匹配（例如高配息但財務結構轉弱應提出警示）

### 輸出格式骨架（僅示意結構，不含真實數字）：

**🏢 公司概況：**
[依 get_company_profile 實際回傳資料摘要]

**💰 獲利能力：**
[依實際回傳的損益表與財務比率數據描述]

**📈 成長性：**
[依實際回傳的月營收與 EPS 數據描述趨勢]

**🏦 財務結構：**
[依實際回傳的資產負債表數據描述體質]

**💵 配息政策：**
[依實際回傳的股利資料描述配息穩定度與殖利率]

**⚖️ 公司治理：**
[依實際回傳的治理評鑑資料描述]

**📝 綜合評語：**
綜合以上「工具實際回傳」的五大面向資料，提出整體體質評語（不得給出未經數據支持的量化分數），並指出資料不足、需進一步查證的部分。

### 本次體檢請求：
股票代號：{stock_symbol}
體檢深度：{depth}

請先呼叫上述對應工具取得真實資料，再依實際回傳內容提供完整的基本面財報體檢。
"""
    return PromptMessage(role="user", content=TextContent(type="text", text=content))
