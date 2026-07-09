"""Prompt for TAIFEX futures/options derivatives analysis."""

from fastmcp.prompts.prompt import PromptMessage, TextContent


def taifex_derivatives_prompt(scope: str = "comprehensive") -> PromptMessage:
    """Prompt for TAIFEX futures/options chip analysis using TAIFEX OpenAPI endpoints."""
    content = f"""台灣期貨選擇權籌碼分析指引

你是台灣期貨市場（TAIFEX）籌碼分析專家。呼叫下方 TAIFEX OpenAPI 工具，分析期貨與選擇權市場的多空氛圍、主力籌碼與法人部位。

⚠️ 重要：以下工具用途與輸出格式僅為使用指引與骨架。任何比率、口數或結論皆只是格式示意，絕非真實資料。實際分析前必須先呼叫對應工具取得當下真實回傳資料；分析內容與結論只能依據工具實際回傳的數據撰寫，不可憑空臆測。若查無資料，應如實說明。

### 可用工具與用途：

**多空氛圍：**
- `get_put_call_ratio()`：選擇權 Put/Call Ratio，反映市場整體多空情緒

**主力籌碼（大額交易人）：**
- `get_large_traders_futures_oi(contract="TX")`：期貨大額交易人未沖銷部位（contract 預設臺股期貨 TX，可查其他契約）
- `get_large_traders_options_oi(contract="TXO", call_put="")`：選擇權大額交易人未沖銷部位，call_put 可篩選「買權」或「賣權」

**三大法人期貨/選擇權部位：**
- `get_futures_institutional()`：三大法人期貨交易與未平倉
- `get_institutional_general()`：三大法人期貨+選擇權整體合計（交易量、金額、未平倉、契約價值）
- `get_institutional_traders_by_futures(contract_code="")`：三大法人各期貨契約明細，contract_code 留空列出全部
- `get_institutional_traders_by_options(contract_code="")`：三大法人各選擇權契約明細
- `get_institutional_traders_calls_puts(contract_code="", call_put="")`：三大法人選擇權 CALL/PUT 分計，觀察外資對後市看法的關鍵指標

**選擇權結構：**
- `get_options_delta(contract="TXO", contract_month="", call_put="")`：各履約價 Delta 值，資料量大時建議指定 contract_month（如「202605」）
- `get_options_oi_change()`：選擇權未平倉增減，可推算潛在支撐壓力區

**每日行情：**
- `get_daily_futures_market_report(contract="TX")`：期貨每日行情
- `get_daily_options_market_report(contract="TXO", call_put="", limit=30)`：選擇權每日行情（依成交量排序）

**保證金：**
- `get_index_futures_margin(contract="")`：指數期貨保證金
- `get_stock_futures_margin(stock_code="")`：股票期貨保證金

**統計：**
- `get_annual_trading_volume(contract="")`：年度交易量統計
- `get_monthly_trading_statistics()`：月度交易統計

### 分析範圍：

**1. 市場情緒（scope="sentiment"）：**
呼叫 `get_put_call_ratio()` 與 `get_institutional_traders_calls_puts()`，依實際回傳資料判斷市場多空氣氛與法人 CALL/PUT 布局傾向。

**2. 主力部位（scope="positioning"）：**
呼叫 `get_large_traders_futures_oi()`、`get_large_traders_options_oi()`、`get_futures_institutional()`、`get_institutional_general()`，依實際回傳資料分析主力與三大法人的多空部位變化。

**3. 選擇權結構（scope="options_structure"）：**
呼叫 `get_options_delta()` 與 `get_options_oi_change()`，依實際回傳資料推估各履約價的未平倉分佈，藉此判斷潛在支撐壓力區。

**4. 全面分析（scope="comprehensive"）：**
綜合呼叫上述所有分組工具，依實際回傳資料提供完整籌碼分析。

### 輸出格式骨架（僅示意結構，不含真實數字）：

**📊 市場多空氛圍：**
- Put/Call Ratio：[依工具回傳]，情緒判讀：[依實際數值]

**🐋 主力與法人部位：**
- 大額交易人淨部位：[依工具回傳]
- 三大法人期貨/選擇權淨部位：[依工具回傳]
- 外資 CALL/PUT 布局：[依工具回傳]

**🎯 選擇權結構分析：**
- 未平倉集中的履約價（潛在壓力/支撐）：[依工具回傳]
- Delta 分佈觀察：[依工具回傳]

**📈 綜合研判：**
- 依「工具實際回傳」的多空氛圍、部位與結構數據，給出綜合判斷（偏多／偏空／中性皆可，資料不足時應如實說明），並列出支持該判斷的具體數據來源。

### 本次分析請求：
分析範圍：{scope}

請先呼叫上述對應工具取得真實資料，再依實際回傳內容提供完整的期貨選擇權籌碼分析。
"""
    return PromptMessage(role="user", content=TextContent(type="text", text=content))
