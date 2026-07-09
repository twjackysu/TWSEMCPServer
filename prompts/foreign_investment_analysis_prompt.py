"""Prompt for foreign investment analysis using TWSE OpenAPI endpoints."""

from fastmcp.prompts.prompt import PromptMessage, TextContent


def foreign_investment_analysis_prompt(analysis_type: str = "overview", industry: str = "", stock_symbol: str = "") -> PromptMessage:
    """Prompt for foreign investment analysis using TWSE OpenAPI endpoints."""
    content = f"""台灣股市外資投資分析指引

你是台灣股市外資投資分析專家。根據使用者要求的分析類型，呼叫下方 TWSE OpenAPI 工具，提供外資投資相關的深入分析。

⚠️ 重要：以下工具用途與輸出格式僅為使用指引與骨架。任何百分比、公司排名或具體數字皆只是格式示意，絕非真實資料。實際分析前必須先呼叫對應工具取得當下真實回傳資料；分析內容與結論只能依據工具實際回傳的數據撰寫，不可憑空臆測、外插或沿用範本中的示意數字。若查無資料，應如實說明。

### 可用工具與用途：

**外資投資總覽：**
- `get_foreign_investment_by_industry()`：各產業外資持股比例
- `get_top_foreign_holdings()`：外資持股前 20 大公司
- `get_company_profile(code)`：公司基本資料（提供背景脈絡）

**進階分析：**
- `get_market_index_info(category, count, format)`：市場環境與類股表現
  - `category="sector", format="summary"`：產業表現總覽
  - `category="major", count=5, format="simple"`：大盤整體情緒
- `get_company_dividend(code)`：外資偏好個股的股利資訊
- `get_stock_valuation_ratios(code)`：本益比、殖利率、股價淨值比
- `get_company_monthly_revenue(code)`：營收表現資料

### 分析類型：

**1. 產業分析（analysis_type="industry"）：**
呼叫 `get_foreign_investment_by_industry()`，依實際回傳資料分析：
- 哪些產業吸引最多外資投資
- 各產業實際外資持股比例
- 各產業中有外資投資的公司家數
- 產業別投資型態

**2. 前 20 大持股分析（analysis_type="top_holdings"）：**
呼叫 `get_top_foreign_holdings()` 與 `get_company_profile()`，依實際回傳資料分析：
- 外資持股前 20 大公司名單
- 可投資空間 vs 目前持股水位
- 投資上限與限制
- 外資偏好個股的公司概況

**3. 個股分析（analysis_type="stock"，需提供 stock_symbol）：**
綜合呼叫多個工具分析 stock_symbol：
- 外資持股水位與投資上限
- 公司基本面與股利政策
- 估值指標與外資投資趨勢的對照

### 輸出格式骨架（僅示意結構，不含真實數字）：

**外資產業投資分析：**
- **[產業名稱]**：外資持股比例 [依工具回傳]、公司家數 [依工具回傳]、驅動因素說明

**外資前 20 大持股洞察：**
1. **[公司名稱]（[代號]）**：外資持股比例 [依工具回傳]、可投資空間 [依工具回傳]、基本面摘要
2. ...

**投資建議：**
根據「工具實際回傳」的外資投資型態，指出：
- 外資高度關注但仍有投資空間的個股
- 基本面支撐外資信心的個股
- 外資配置比例呈上升趨勢的產業

### 本次分析請求：
分析類型：{analysis_type}
{f"目標產業：{industry}" if industry else ""}
{f"目標股票：{stock_symbol}" if stock_symbol else ""}

請先呼叫上述對應工具取得真實資料，再依實際回傳內容提供完整的外資投資分析。
"""
    return PromptMessage(role="user", content=TextContent(type="text", text=content))
