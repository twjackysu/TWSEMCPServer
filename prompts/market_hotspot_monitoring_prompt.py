"""Prompt for market hotspot monitoring using TWSE OpenAPI endpoints."""

from fastmcp.prompts.prompt import PromptMessage, TextContent


def market_hotspot_monitoring_prompt(monitoring_scope: str = "comprehensive", date_filter: str = "today") -> PromptMessage:
    """Prompt for market hotspot monitoring using TWSE OpenAPI endpoints."""
    content = f"""台灣股市熱點監控指引

你是台灣股市監控專家。呼叫下方 TWSE OpenAPI 工具，找出市場熱點、趨勢股與重要市場動態。

⚠️ 重要：以下工具用途與輸出格式僅為使用指引與骨架。任何公司名稱、事件或數字皆只是格式示意，絕非真實資料。實際分析前必須先呼叫對應工具取得當下真實回傳資料；分析內容與結論只能依據工具實際回傳的數據撰寫，不可憑空臆測。若查無資料，應如實說明。

### 熱點偵測可用工具：

**新聞與公告：**
- `get_company_major_news(code="", date="", market="")`：重大訊息。指定 code 看該公司全年公告（含說明全文）；不指定則列出某日全市場公告主旨，market 可篩 sii 上市、otc 上櫃、rotc 興櫃、pub 公發
- `get_investor_conferences(year, month)`：該月法人說明會行事曆
- `get_treasury_stock_buybacks()`：近期庫藏股買回案件（公司護盤訊號）
- `get_twse_news(start_date, end_date)`：證交所最新官方新聞（可依日期篩選）
- `get_twse_events(top=10)`：證交所活動與事件

**市場活動指標：**
- `get_real_time_trading_stats()`：即時市場統計
- `get_market_index_info(date, category, keyword)`：市場指數分析（可彈性篩選）
  - `get_market_index_info(category="major")`：快速掌握大盤概況
  - `get_market_index_info(category="sector")`：找出熱門類股
  - `get_market_index_info(category="thematic")`：熱門主題（AI、5G、ESG 等）
- `get_daily_day_trading_targets()`：全市場當沖占比與當沖量大的個股
- `get_stock_daily_trading(stock_no=code)`：個股日成交量與價格變動
- `get_etf_regular_investment_ranking()`：熱門定期定額投資趨勢
- `get_foreign_holdings(sort_by="ratio", limit=20)`：外資流向指標

**總體環境：**
- `get_business_cycle_indicators()`：景氣對策信號（燈號與分數）
- `get_taiwan_pmi()`：製造業 PMI 與非製造業 NMI
- `get_exchange_rates(currency="NTD")`：新台幣匯率走勢

**公司行動：**
- `get_dividend_rights_schedule(code)`：即將除權息日期
- `get_warrant_daily_trading(code)`：權證交易活躍度（投機指標）

### 監控範圍：

**1. 即時新聞監控（monitoring_scope="news"）：**
呼叫 `get_company_major_news()` 與 `get_twse_news(start_date, end_date)`，依實際回傳資料找出：
- 今日有重大公告的公司
- 法規變動或政策更新
- 影響市場的新聞與公司行動
- 產業別重大動態

**2. 交易活動熱點（monitoring_scope="trading"）：**
呼叫交易相關工具，依實際回傳資料找出：
- 成交量或價格異常波動的個股
- 定期定額熱門度上升的 ETF
- 反映市場投機氣氛的權證活動
- 外資投資流向變化

**3. 全面市場掃描（monitoring_scope="comprehensive"）：**
綜合呼叫上述工具，依實際回傳資料提供：
- 影響多個產業的重大新聞
- 成交量與外資流向型態
- 即將發生的公司行動及其潛在影響
- 整體市場情緒指標

### 分析流程：

**步驟一：新聞影響評估**
- 依實際回傳的公告內容，篩選具市場影響力者
- 找出近期多次發布公告的公司
- 評估法規或政策對產業的影響

**步驟二：交易型態分析**
- 依實際回傳資料比對成交量與歷史水位
- 找出外資流向的變化
- 觀察 ETF 與權證活躍度反映的情緒

**步驟三：前瞻指標**
- 影響未來股價的即將除權息日期
- 可能帶動未來交易的公司行動
- 可能影響市場結構的證交所事件

### 輸出格式骨架（僅示意結構，不含真實數字）：

**市場熱點總覽：**
🔥 **今日焦點（依工具實際回傳資料填寫）：**
1. **[公司/產業]**：關注原因、相關新聞、交易面影響
2. ...

📈 **交易活動警示：**
- 依實際回傳資料列出高量個股與對應新聞
- 外資流向變化
- 熱門投資趨勢（ETF 排行）

📅 **未來事件：**
- 未來 5 個交易日內的除權息日期（依工具實際回傳）
- 重要證交所公告或事件
- 待觀察的公司行動

🎯 **投資意涵：**
- 短期交易機會
- 中期趨勢轉變
- 需留意的風險因子

### 本次監控請求：
監控範圍：{monitoring_scope}
日期篩選：{date_filter}

請先呼叫上述對應工具取得真實資料，再依實際回傳內容提供完整的市場熱點分析。
"""
    return PromptMessage(role="user", content=TextContent(type="text", text=content))
