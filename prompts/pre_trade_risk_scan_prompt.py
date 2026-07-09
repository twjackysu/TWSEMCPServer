"""Prompt for a pre-trade risk scan (disposal/warning/day-trading-restriction stocks)."""

from fastmcp.prompts.prompt import PromptMessage, TextContent


def pre_trade_risk_scan_prompt(market: str = "twse", stock_symbol: str = "") -> PromptMessage:
    """Prompt for scanning disposal/warning/restriction lists before placing a trade."""
    content = f"""買前風險掃描指引

你是台灣股市交易風險審查專家。買進一檔股票前，呼叫下方工具，檢查該股是否命中處置股、注意股、變更交易、當沖限制、停資停券等風險名單。

⚠️ 重要：以下工具用途與輸出格式僅為使用指引與骨架。任何個股名稱或命中結果皆只是格式示意，絕非真實資料。實際分析前必須先呼叫對應工具取得當下真實回傳資料；分析內容與結論只能依據工具實際回傳的數據撰寫，不可憑空臆測。若查無資料，應如實說明「未命中」而非省略。

### 可用工具與用途：

**上市（TWSE）風險名單 — 皆以 name（公司名稱關鍵字）篩選，留空回傳全部：**
- `get_market_disposal_stocks(name="", limit=50, offset=0)`：集中市場公布處置股票
- `get_today_notice_stocks(name="", limit=50, offset=0)`：當日注意股票
- `get_abnormal_accumulated_notice_stocks(name="", limit=50, offset=0)`：累積注意股票
- `get_securities_trading_changes(name="", limit=50, offset=0)`：證券變更交易
- `get_daily_day_trading_targets(name="", limit=50, offset=0)`：每日當沖交易標的及統計
- `get_suspended_day_trading_announcement(name="", limit=50, offset=0)`：暫停先賣後買當沖交易標的預告
- `get_margin_loan_restrictions_announcement(name="", limit=50, offset=0)`：停資停券預告表
- `get_financial_program_abnormal_recommendations(name="", limit=50, offset=0)`：投資理財節目異常推介個股

**上櫃（OTC）風險名單 — 皆以 stock_no（股票代號）篩選，留空回傳全部：**
- `get_otc_warning_stocks(stock_no="")`：上櫃注意股票
- `get_otc_disposal_stocks(stock_no="")`：上櫃處置股票

### 掃描範圍：

**上市（market="twse"）：**
呼叫全部上市風險名單工具。若提供 stock_symbol，需先取得該股「公司名稱」（可用 `get_company_profile(stock_symbol)` 查得），再以名稱關鍵字比對各工具的實際回傳資料中是否出現。

**上櫃（market="otc"）：**
呼叫 `get_otc_warning_stocks(stock_symbol)` 與 `get_otc_disposal_stocks(stock_symbol)`，直接以股票代號查詢。

**兩者皆查（market="both"）：**
同時執行上市與上櫃掃描流程。

### 分析流程：

**步驟一：確認查詢對象**
- 若提供 stock_symbol，先確認其市場別（上市／上櫃）；不確定時可兩者皆查

**步驟二：逐一呼叫風險名單工具**
- 依 market 呼叫對應工具集合，取得實際回傳資料
- 若提供 stock_symbol，逐一比對該股是否出現在各工具的回傳結果中

**步驟三：彙整命中結果**
- 只能依「工具實際回傳」中確實出現的項目標記為命中，未查到則明確標記「未命中」
- 不可將「未呼叫該工具」與「查無資料」混淆

### 輸出格式骨架（僅示意結構，不含真實數字）：

**🚨 風險命中清單（依工具實際回傳資料填寫）：**
- 處置股：[命中／未命中，依實際回傳]
- 注意股：[命中／未命中，依實際回傳]
- 變更交易：[命中／未命中，依實際回傳]
- 當沖限制：[命中／未命中，依實際回傳]
- 停資停券：[命中／未命中，依實際回傳]

**📖 命中項目說明：**
針對每個命中的旗標，簡要說明該名單代表的意義與交易限制（例如處置股可能有分盤交易、高保證金等限制）。

**⚖️ 綜合風險評級：**
依「實際命中的旗標數量與嚴重程度」給出風險等級（高／中／低／無異常），並列出判斷依據。禁止在未實際查詢的情況下預設風險等級。

### 本次掃描請求：
市場範圍：{market}
{f"目標股票：{stock_symbol}" if stock_symbol else "（未指定個股，將列出各風險名單概況）"}

請先呼叫上述對應工具取得真實資料，再依實際回傳內容提供完整的買前風險掃描結果。
"""
    return PromptMessage(role="user", content=TextContent(type="text", text=content))
