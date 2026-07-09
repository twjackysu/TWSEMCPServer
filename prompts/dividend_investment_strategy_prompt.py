"""Prompt for dividend investment strategy using TWSE OpenAPI endpoints."""

from fastmcp.prompts.prompt import PromptMessage, TextContent


def dividend_investment_strategy_prompt(strategy_type: str = "high_yield", time_horizon: str = "quarterly") -> PromptMessage:
    """Prompt for dividend investment strategy using TWSE OpenAPI endpoints."""
    content = f"""台灣股市股利投資策略指引

你是台灣股市股利投資策略專家。呼叫下方 TWSE OpenAPI 工具，制定完整的股利投資策略。

⚠️ 重要：以下工具用途與輸出格式僅為使用指引與骨架。任何殖利率、日期或個股排名皆只是格式示意，絕非真實資料。實際分析前必須先呼叫對應工具取得當下真實回傳資料；分析內容與結論只能依據工具實際回傳的數據撰寫，不可憑空臆測或沿用範本中的示意數字。若查無資料，應如實說明。

### 股利分析可用工具：

**除權息排程與規劃：**
- `get_dividend_rights_schedule(code)`：除權息日期與股利金額
- `get_company_dividend(code)`：歷史股利發放資料
- `get_stock_valuation_ratios(code)`：本益比、殖利率、股價淨值比

**基本面分析：**
- `get_company_profile(code)`：公司基本資料與產業分類
- `get_company_monthly_revenue(code)`：支撐配息永續性的營收趨勢
- `get_company_income_statement(code)`：計算配息率所需的獲利資料
- `get_company_balance_sheet(code)`：財務體質評估

**市場驗證：**
- `get_top_foreign_holdings()`：外資偏好的股利股
- `get_etf_regular_investment_ranking()`：熱門定期定額投資標的
- `get_stock_daily_trading(code)`：除權息前後的股價穩定度

### 投資策略類型：

**1. 高殖利率策略（strategy_type="high_yield"）：**
鎖定殖利率具吸引力的個股：
- 呼叫 `get_stock_valuation_ratios()`，依實際回傳資料篩選高殖利率個股
- 以 `get_company_income_statement()` 與營收趨勢驗證配息永續性
- 呼叫 `get_dividend_rights_schedule()` 確認即將發放的股利
- 以 `get_top_foreign_holdings()` 評估外資關注度

**2. 股利成長策略（strategy_type="growth"）：**
鎖定股利持續成長的公司：
- 分析 `get_company_dividend()` 的歷史股利成長軌跡
- 對照 `get_company_monthly_revenue()` 確認營收成長支撐
- 以 `get_company_balance_sheet()` 確認財務體質穩健
- 觀察外資投資趨勢作為品質驗證

**3. 除權息時機策略（strategy_type="timing"）：**
優化除權息前後的進出場時機：
- 呼叫 `get_dividend_rights_schedule()` 掌握精確時程
- 分析 `get_stock_daily_trading()` 的歷史價格型態
- 以 `get_stock_valuation_ratios()` 評估合理價位
- 納入即將公告的股利資訊

**4. 產業股利策略（strategy_type="sector"）：**
鎖定配息穩定的產業：
- 透過 `get_company_profile()` 依產業分類個股
- 比較各產業殖利率與配息永續性
- 分析外資的產業偏好
- 於穩定配息產業間分散布局

### 時間週期分析：

**季度視角（time_horizon="quarterly"）：**
- 未來 3 個月除權息排程
- 季度獲利對配息永續性的影響
- 除息日前後的短期價格波動

**年度規劃（time_horizon="annual"）：**
- 全年除權息行事曆規劃
- 年度股利成長趨勢分析
- 長期產業輪動策略

### 分析流程：

**步驟一：股利篩選**
- 依目標殖利率或成長率篩選
- 確認即將到來的除權息日期與金額
- 檢視歷史配息穩定度

**步驟二：基本面驗證**
- 評估獲利覆蓋率與配息率
- 檢視營收穩定度與成長趨勢
- 分析資產負債結構與現金流

**步驟三：市場定位**
- 對照外資投資偏好
- 觀察熱門股利投資趨勢
- 評估市場時機與估值水位

### 輸出格式骨架（僅示意結構，不含真實數字）：

**📊 股利投資建議：**

**優選股利股：**
1. **[公司名稱]（[代號]）**：殖利率 [依工具回傳]、除息日 [依工具回傳]、選股理由
2. ...

**📅 除權息行事曆（未來 3 個月）：**
- 依 `get_dividend_rights_schedule()` 實際回傳資料，依週別列出除權息個股與預估殖利率

**🎯 策略洞察：**
- **風險評估**：配息永續性因子
- **進場時機**：合適的買進時間窗
- **投資組合建構**：分散配置建議
- **市場環境**：當前股利投資環境分析

**💡 進階策略：**
- 除權息套利機會
- 依股利週期進行的產業輪動
- 稅務考量
- 外資流向的意涵

### 本次策略請求：
策略類型：{strategy_type}
時間週期：{time_horizon}

請先呼叫上述對應工具取得真實資料，再依實際回傳內容提供完整的股利投資策略。
"""
    return PromptMessage(role="user", content=TextContent(type="text", text=content))
