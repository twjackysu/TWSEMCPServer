# 🚀 TWStockMCPServer

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![MCP](https://img.shields.io/badge/MCP-Compatible-green.svg)](https://modelcontextprotocol.io/)

一個全面的**模型上下文協議 (MCP) 伺服器**，專為台灣證券交易所 (TWSE) 數據分析設計，提供即時股票資訊、財務報表、ESG 數據和趨勢分析功能。

<a href="https://glama.ai/mcp/servers/@twjackysu/TWSEMCPServer">
  <img width="380" height="200" src="https://glama.ai/mcp/servers/@twjackysu/TWSEMCPServer/badge" />
</a>

## 🌏 語言版本

- [English](README_en-us.md) | **繁體中文**

## 🎬 示範影片

![股票趨勢分析示範](./staticFiles/sample-ezgif.com-resize.gif)

*觀看 TWStockMCPServer 功能展示*

## ✨ 主要功能

### 📊 **技術分析工具**
- **每日交易數據**：即時股價、成交量和交易統計
- **價格趨勢**：每日收盤價和月平均價格計算
- **估值指標**：本益比、股利殖利率和股價淨值比
- **歷史數據**：月份和年度交易資訊
- **即時統計**：每 5 秒更新的委託成交統計

### 💰 **基本面分析**
- **財務報表**：綜合損益表和資產負債表（一般業）
- **營收報告**：月營收追蹤和成長分析
- **股利資訊**：配息記錄和股利政策
- **公司治理**：ESG 數據和治理指標

### 🏛️ **市場情報**
- **市場指數**：即時台股指數資訊和歷史資料
- **法人動態**：融資融券和借貸數據
- **市場統計**：每日市場摘要和長期趨勢分析

### 🌱 **ESG 與永續經營**
- **氣候管理**：氣候相關風險評估
- **風險管理**：企業風險管理政策
- **供應鏈**：供應鏈管理透明度
- **資訊安全**：網路安全事件報告

## ⚙️ 安裝說明

### 🚀 方式一：直接使用線上服務（推薦）

感謝 FastMCP Cloud 提供的免費託管服務（暫時免費），您可以直接使用以下配置連接我的 MCP Server：

```json
{
  "twstockmcpserver": {
    "transport": "streamable_http",
    "url": "https://TW-Stock-MCP-Server.fastmcp.app/mcp"
  }
}
```

### 🔧 方式二：本地安裝

#### 系統需求
- Python 3.13 或更高版本
- pip 套件管理器或 [uv](https://github.com/astral-sh/uv)（推薦）

#### 快速開始

1. **複製專案**
   ```bash
   git clone https://github.com/yourusername/TWStockMCPServer.git
   cd TWStockMCPServer
   ```

2. **安裝相依套件**
   
   **使用 pip：**
   ```bash
   pip install -r requirements.txt
   ```
   
   **使用 uv（推薦）：**
   ```bash
   uv sync
   ```

3. **啟動伺服器**
   
   **開發模式（熱重載）：**
   ```bash
   uv run fastmcp dev server.py
   ```
   
   **正式環境模式：**
   ```bash
   uv run fastmcp run server.py
   ```

## 🎯 五大核心問題情境

### 1. **股票趨勢分析** (`stock_trend_analysis_prompt`)
**可回答的問題：**
- "請分析台積電(2330)的短期趨勢"
- "幫我看看長榮(2603)的中期走勢如何"
- "鴻海(2317)的長期投資價值分析"

**使用工具：** 15個工具涵蓋技術、基本面、籌碼、消息、ESG分析

### 2. **外資投資分析** (`foreign_investment_analysis`)
**可回答的問題：**
- "外資最喜歡投資哪些產業？"
- "目前外資持股前20名是哪些公司？"
- "聯發科(2454)的外資投資狀況如何？"
- "半導體產業的外資投資趨勢分析"

**使用工具：** 6個工具專注外資流向和基本面驗證

### 3. **市場熱點監控** (`market_hotspot_monitoring`)
**可回答的問題：**
- "今天市場有什麼重大消息？"
- "哪些股票交易量異常活躍？"
- "本週有什麼重要的除權息行程？"
- "目前市場投機氣氛如何？"

**使用工具：** 8個工具監控新聞、交易活動、公司動作

### 4. **股利投資策略** (`dividend_investment_strategy`)
**可回答的問題：**
- "推薦一些高殖利率股票"
- "下季有哪些公司要除權息？"
- "股利成長型投資組合建議"
- "金融股的股利投資機會分析"

**使用工具：** 9個工具專注股利分析和財務評估

### 5. **投資篩選建議** (`investment_screening`)
**可回答的問題：**
- "推薦一些價值型投資標的"
- "成長股篩選條件和建議"
- "保守型投資者適合的股票"
- "目前哪些股票被外資看好？"

**使用工具：** 12個工具進行全方位篩選和風險評估

## 📚 可用工具

### 公司資訊（13個工具）
**基本資訊與新聞：**
- `get_company_profile(code)` - 公司基本資訊
- `get_company_dividend(code)` - 股利分配數據
- `get_company_monthly_revenue(code)` - 月營收報告
- `get_company_major_news(code)` - 公司重大訊息公告
- `get_twse_news()` - 證交所官方新聞
- `get_twse_events()` - 證交所活動公告

**財務報表：**
- `get_company_income_statement(code)` - 綜合損益表（一般業）
- `get_company_balance_sheet(code)` - 資產負債表（一般業）

**ESG 與治理：**
- `get_company_governance_info(code)` - 公司治理
- `get_company_climate_management(code)` - 氣候相關管理
- `get_company_risk_management(code)` - 風險管理政策
- `get_company_supply_chain_management(code)` - 供應鏈數據
- `get_company_info_security(code)` - 資訊安全指標

### 交易數據（10個工具）
- `get_stock_daily_trading(code)` - 每日交易統計
- `get_stock_monthly_average(code)` - 月平均價格
- `get_stock_valuation_ratios(code)` - 估值指標（本益比、殖利率、股價淨值比）
- `get_stock_monthly_trading(code)` - 月交易數據
- `get_stock_yearly_trading(code)` - 年度交易統計
- `get_dividend_rights_schedule(code)` - 除權息日程
- `get_etf_regular_investment_ranking()` - ETF定期定額投資排行
- `get_warrant_basic_info(code)` - 權證基本資料
- `get_warrant_daily_trading(code)` - 權證每日交易量值
- `get_warrant_trader_count()` - 權證每日交易人數

### 市場數據（6個工具）
- `get_market_index_info()` - 市場指數資訊
- `get_margin_trading_info()` - 融資融券統計
- `get_real_time_trading_stats()` - 即時交易統計（每 5 秒更新）
- `get_market_historical_index()` - 發行量加權股價指數歷史資料
- `get_foreign_investment_by_industry()` - 外資及陸資投資統計（依行業別）
- `get_top_foreign_holdings()` - 外資及陸資投資統計（前20名）

## 🤝 參與貢獻

歡迎開發者社群參與貢獻！您可以透過以下方式協助：

### 貢獻方式

1. **新增工具**：擴展 API 覆蓋範圍，實作新的 TWSE 端點
2. **改善文件**：協助改進範例和說明文件
3. **修復錯誤**：回報和修復問題
4. **功能建議**：提出新功能想法
5. **測試**：新增測試案例和提升可靠性

### 開發環境設定

1. **Fork 專案**
2. **建立功能分支**
   ```bash
   git checkout -b feature/your-new-tool
   ```
3. **在 `server.py` 中新增您的工具**
   ```python
   @mcp.tool
   def your_new_tool(code: str) -> str:
       """您的工具說明。"""
       # 實作內容
   ```
4. **更新說明文件**
5. **提交 Pull Request**

### API 參考
參考 `staticFiles/apis_summary_simple.json` 查看可實作為新工具的可用 TWSE API 端點。

### 程式碼風格
- 遵循 Python PEP 8 指南
- 新增完整的 docstrings
- 包含錯誤處理
- 記錄重要操作

## 🔒 資料來源

所有資料來源自台灣證券交易所 (TWSE) 官方開放 API：
- 基礎 URL：`https://openapi.twse.com.tw/v1`
- 即時和歷史資料
- 無需 API 金鑰
- 適用速率限制

## ⚠️ 免責聲明

本軟體僅供參考之用，不構成投資建議。使用者應進行自己的研究，並在做出投資決定前諮詢財務專業人士。由於我不熟悉 Python，該專案完全由 AI 生成，然後根據需要手動調整。

## 📄 授權條款

本專案採用 MIT 授權條款 - 詳見 [LICENSE](LICENSE) 檔案。

## 🙏 致謝

- 台灣證券交易所提供開放資料 API
- [FastMCPCloud](https://fastmcp.app/) 提供免費 MCP 伺服器託管服務
- MCP 社群提供協議規範
- 本專案的貢獻者和使用者

---

**以 ❤️ 為台灣股票分析社群打造**

