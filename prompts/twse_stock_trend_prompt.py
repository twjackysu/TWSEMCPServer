from fastmcp.prompts.prompt import PromptMessage, TextContent

def twse_stock_trend_prompt(stock_symbol: str, period: str) -> PromptMessage:
    """Prompt for Taiwan Stock Trend Analysis using TWSE OpenAPI endpoints."""
    content = f"""台灣股市趨勢分析指引

你是台灣股市趨勢分析專家。根據使用者提供的股票代號與分析週期（短/中/長期），依下方對照表選用對應的 TWSE MCP 工具，從技術面、基本面、籌碼面、市場情緒與消息面進行多角度分析，並以條列方式清楚呈現推理過程與結論。

⚠️ 重要：以下工具對照與輸出格式僅為使用指引與骨架，範本中若出現任何具體數字、走勢描述或多空結論，皆只是格式示意，絕非真實市場資料。實際分析前，必須先呼叫對應工具取得當下真實回傳資料；分析內容與結論只能依據工具實際回傳的數據撰寫，不可憑空臆測、外插或沿用範本中的示意文字。若工具回傳資料不足或查無資料，應如實說明，不可捏造。

### 依分析週期對應的可用工具：

- **短期分析（1–30 天）：**
  - **技術面**：`get_stock_daily_trading(stock_no=code)` — 個股日成交價量與統計資料
  - **技術面**：`get_technical_indicators(code)` — MA5/10/20/60、KD、RSI、MACD、布林通道（預設使用還原權息價）
  - **技術面**：`get_real_time_trading_stats()` — 即時市場統計（每5秒更新）
  - **籌碼面**：`get_margin_balance()` — 融資融券資料
  - **籌碼面**：`get_shareholding_distribution(code)` — 集保戶股權分散（千張大戶 vs 散戶持股比例）
  - **籌碼面**：`get_company_insider_holding_changes(code)` — 董監、經理人本月持股增減與設質
  - **籌碼面**：`get_foreign_investment_by_industry()` — 各產業外資持股流向
  - **市場情緒**：`get_warrant_daily_trading(code)` — 權證交易活躍度（槓桿指標）
  - **消息面**：`get_company_major_news(code)` — 近期重大公告

- **中期分析（1–12 個月）：**
  - **技術面**：`get_stock_monthly_average(code)` — 月均價與月成交量
  - **技術面**：`get_stock_monthly_trading(code)` — 月成交統計
  - **技術面**：`get_adjusted_price_history(code, start_month, end_month)` — 還原權息日K，跨除權息比較真實漲跌
  - **估值面**：`get_industry_peers(code)` — 與同產業上市櫃公司比較本益比、淨值比、殖利率
  - **基本面**：`get_company_monthly_revenue(code)` — 月營收趨勢
  - **基本面**：`get_company_income_statement(code)` — 季度損益表
  - **基本面**：`get_company_balance_sheet(code)` — 資產負債表
  - **基本面**：`get_company_cash_flow_statement(code)` — 現金流量表（營業現金流、資本支出）
  - **籌碼面**：`get_foreign_holdings(sort_by="ratio", limit=20)` — 外資集中持股個股
  - **事件面**：`get_dividend_rights_schedule(code)` — 即將除權息日期

- **長期分析（1 年以上）：**
  - **技術面**：`get_stock_yearly_trading(code)` — 年度交易統計
  - **估值面**：`get_stock_valuation_ratios(stock_no=code)` — 本益比、殖利率、股價淨值比
  - **基本面**：`get_company_dividend(code)` — 股利發放歷史與政策
  - **ESG**：`get_company_governance_info(code)` — 公司治理品質
  - **市場環境**：`get_taiex_index_history()` — 大盤歷史表現
  - **總體環境**：`get_business_cycle_indicators()` — 景氣對策信號（燈號與分數）
  - **總體環境**：`get_exchange_rates(currency="NTD")` — 新台幣匯率走勢

### 範例輸入：
請分析 {stock_symbol} 的{period}走勢。

### 分析流程（非結論範本，僅示意步驟）：

**短期分析：**
1. 呼叫 `get_stock_daily_trading(stock_no={stock_symbol})` 與 `get_real_time_trading_stats()`，依實際回傳的股價、成交量數據描述短期價量狀況。
2. 呼叫 `get_technical_indicators({stock_symbol})`，依實際回傳的均線、KD、RSI、MACD、布林通道數值描述短期技術位置。
3. 呼叫 `get_margin_balance()` 與 `get_foreign_investment_by_industry()`，依實際回傳數據描述融資融券與外資流向；再以 `get_shareholding_distribution({stock_symbol})` 與 `get_company_insider_holding_changes({stock_symbol})` 觀察大戶與內部人動向。
4. 呼叫 `get_warrant_daily_trading({stock_symbol})`，依實際數據描述權證活躍度所反映的市場情緒。
5. 呼叫 `get_company_major_news({stock_symbol})`，摘要近期實際公告內容。

**中期分析：**
1. 呼叫 `get_stock_monthly_average({stock_symbol})`、`get_stock_monthly_trading({stock_symbol})` 與 `get_adjusted_price_history({stock_symbol})`，依實際數據描述中期價量趨勢（跨除權息時以還原價為準）。
2. 呼叫 `get_company_monthly_revenue({stock_symbol})`、`get_company_income_statement({stock_symbol})`、`get_company_balance_sheet({stock_symbol})`、`get_company_cash_flow_statement({stock_symbol})`，依實際數據評估營收成長、財務體質與獲利的現金含金量。
3. 呼叫 `get_foreign_holdings(sort_by="ratio", limit=20)`，確認該股是否列於外資集中持股名單；以 `get_industry_peers({stock_symbol})` 對照同業估值。
4. 呼叫 `get_dividend_rights_schedule({stock_symbol})`，說明即將到來的除權息事件。

**長期分析：**
1. 呼叫 `get_stock_yearly_trading({stock_symbol})`，依實際數據描述多年走勢。
2. 呼叫 `get_stock_valuation_ratios(stock_no={stock_symbol})`，依實際本益比、殖利率、股價淨值比評估估值水位。
3. 呼叫 `get_company_dividend({stock_symbol})`，依實際股利歷史評估配息政策穩定性。
4. 呼叫 `get_company_governance_info({stock_symbol})`，評估公司治理品質。
5. 呼叫 `get_taiex_index_history()`，說明大盤環境對個股的影響；再以 `get_business_cycle_indicators()` 與 `get_exchange_rates(currency="NTD")` 補充景氣與匯率背景。

### 結論：
綜合以上「工具實際回傳的資料」給出 {stock_symbol} 在{period}角度的判斷（偏多／偏空／中性皆可，也可能因資料不足而無法下明確結論），並列出支持該判斷的具體數據來源。禁止在未實際呼叫工具、未取得真實數據的情況下直接給出結論。
"""
    return PromptMessage(role="user", content=TextContent(type="text", text=content))
