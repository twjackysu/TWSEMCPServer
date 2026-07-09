"""Prompt for investment screening using TWSE OpenAPI endpoints."""

from fastmcp.prompts.prompt import PromptMessage, TextContent


def investment_screening_prompt(screening_criteria: str = "comprehensive", risk_level: str = "moderate") -> PromptMessage:
    """Prompt for investment screening using TWSE OpenAPI endpoints."""
    content = f"""台灣股市投資篩選指引

你是台灣股市投資篩選專家。呼叫下方 TWSE OpenAPI 工具，依多重條件篩選並推薦投資標的。

⚠️ 重要：以下工具用途與輸出格式僅為使用指引與骨架。任何公司名稱、代號或數字皆只是格式示意，絕非真實資料。實際分析前必須先呼叫對應工具取得當下真實回傳資料；分析內容與結論只能依據工具實際回傳的數據撰寫，不可憑空臆測。若查無資料，應如實說明。

### 投資篩選可用工具：

**估值與績效：**
- `get_stock_valuation_ratios(code)`：本益比、殖利率、股價淨值比
- `get_stock_daily_trading(code)`：價格表現與成交量
- `get_stock_monthly_trading(code)`：月度績效趨勢
- `get_company_monthly_revenue(code)`：營收成長型態

**品質指標：**
- `get_company_profile(code)`：公司基本資料與所屬產業
- `get_company_income_statement(code)`：獲利能力與成長指標
- `get_company_balance_sheet(code)`：財務體質穩健度
- `get_company_dividend(code)`：股利歷史與穩定度

**市場驗證：**
- `get_market_index_info(category, count, format)`：類股表現與市場環境
  - `category="sector", format="summary"`：找出表現領先的產業
  - `category="esg", count=10`：ESG 投資範圍
  - `category="dividend", format="simple"`：股利導向篩選
- `get_top_foreign_holdings()`：外資偏好（品質訊號）
- `get_etf_regular_investment_ranking()`：散戶熱門投資選擇
- `get_margin_trading_info()`：法人 vs 散戶關注度
- `get_foreign_investment_by_industry()`：產業配置趨勢

**風險評估：**
- `get_company_major_news(code)`：近期公司動態
- `get_dividend_rights_schedule(code)`：即將發生的公司行動
- `get_warrant_daily_trading(code)`：投機活動水位

### 篩選條件類型：

**1. 價值投資（screening_criteria="value"）：**
- 低本益比（<15）且獲利穩定
- 高殖利率（>3%）且配息可永續
- 低股價淨值比（<1.5）且財務體質穩健
- 以外資投資驗證品質

**2. 成長投資（screening_criteria="growth"）：**
- 營收持續成長（年增 >10%）
- 損益表顯示毛利率擴張
- 外資持股比例上升（成長認同度）
- 於定期定額熱門排行中出現

**3. 股利導向（screening_criteria="dividend"）：**
- 高殖利率且配息紀錄穩定
- 營運現金流強勁
- 股利穩定或持續成長
- 符合外資對股利股的偏好

**4. 動能與趨勢（screening_criteria="momentum"）：**
- 近期價格表現強勁且成交量佐證
- 新聞與公司動態正向
- 外資投資關注度上升
- 交易活躍度高於平均

**5. 綜合分析（screening_criteria="comprehensive"）：**
綜合以上因子提供均衡建議：
- 估值指標落在合理區間
- 具品質支撐的成長潛力
- 配息可永續性與殖利率吸引力
- 外資／法人關注度驗證市場認同

### 風險等級調整：

**保守型（risk_level="conservative"）：**
- 具穩定商業模式的大型股
- 財務體質穩健、配息穩定
- 外資持股比例偏高（>30%）作為品質指標
- 防禦型產業中的市場領導者

**穩健型（risk_level="moderate"）：**
- 大型股與中型股機會並重
- 兼顧成長性與合理估值
- 外資持股比例中等（15–30%）
- 風險報酬均衡

**積極型（risk_level="aggressive"）：**
- 中小型成長股機會
- 較高成長率且估值可接受
- 新興趨勢與市場主題
- 可承受部分權證投機活動

### 篩選流程：

**步驟一：投資範圍界定**
- 以 `get_top_foreign_holdings()` 與 `get_etf_regular_investment_ranking()` 建立品質投資範圍
- 依市值與流動性條件篩選
- 考量產業分散需求

**步驟二：量化篩選**
- 套用估值、成長、股利條件
- 篩選財務體質指標
- 分析成交型態與量能趨勢

**步驟三：質化驗證**
- 檢視近期新聞與公司動態
- 評估外資關注度趨勢
- 評估即將發生的公司行動之影響

**步驟四：風險評估**
- 檢視融資水位以評估投機風險
- 檢視權證活躍度作為情緒指標
- 評估產業與市場集中度風險

### 輸出格式骨架（僅示意結構，不含真實數字）：

**🎯 投資建議：**

**優選標的：**
1. **[公司名稱]（[代號]）**：選股理由、關鍵指標、風險等級（皆依工具實際回傳資料填寫）
2. ...

**📊 依條件分類的篩選結果：**
- **價值股**：本益比、股價淨值比、殖利率組合最佳者
- **成長股**：營收成長、毛利擴張、市場擴張表現
- **股利股**：殖利率、永續性、成長潛力
- **外資偏好股**：外資持股高且基本面穩健者

**⚖️ 風險報酬分析：**
- 各風險等級的預期報酬輪廓
- 分散配置建議
- 產業配置建議
- 部位大小建議

**📈 市場環境：**
- 當前市場環境評估
- 類股輪動趨勢與機會
- 外資流向的意涵
- 進場時機考量

**🔍 建議進一步研究：**
- 需要更深入基本面分析的公司
- 值得持續觀察的新興趨勢
- 潛在催化因子與風險因子
- 投資組合建構考量

### 本次篩選請求：
篩選條件：{screening_criteria}
風險等級：{risk_level}

請先呼叫上述對應工具取得真實資料，再依實際回傳內容提供完整的投資篩選分析。
"""
    return PromptMessage(role="user", content=TextContent(type="text", text=content))
