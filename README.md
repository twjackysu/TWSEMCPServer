# 🚀 TWStockMCPServer

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
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

### 💰 **基本面分析**
- **財務報表**：綜合損益表和資產負債表
- **營收報告**：月營收追蹤和成長分析
- **股利資訊**：配息記錄和股利政策
- **公司治理**：ESG 數據和治理指標

### 🏛️ **市場情報**
- **市場指數**：即時台股指數資訊
- **法人動態**：融資融券和借貸數據
- **市場統計**：每日市場摘要和趨勢

### 🌱 **ESG 與永續經營**
- **氣候管理**：氣候相關風險評估
- **風險管理**：企業風險管理政策
- **供應鏈**：供應鏈管理透明度
- **資訊安全**：網路安全事件報告

## ⚙️ 安裝說明

### 系統需求
- Python 3.8 或更高版本
- pip 套件管理器或 [uv](https://github.com/astral-sh/uv)

### 快速開始

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
   uv venv
   .venv\Scripts\activate  # Windows
   # 或
   source .venv/bin/activate  # macOS/Linux
   uv add mcp[cli] httpx fastmcp requests
   ```

3. **設定 MCP 客戶端**
   
   在您的 MCP 客戶端設定檔中新增（例如：`.vscode/mcp.json`）：
   ```json
   {
     "servers": {
       "twse_stock_server": {
         "type": "stdio",
         "command": "python",
         "args": ["${workspaceFolder}/server.py"]
       }
     }
   }
   ```

4. **啟動伺服器**
   
   **開發模式（熱重載）：**
   ```bash
   uv run fastmcp dev server.py
   ```
   
   **正式環境模式：**
   ```bash
   uv run fastmcp run server.py
   # 或
   python server.py
   ```

## 🔧 設定

### 環境變數
在專案根目錄建立 `.env` 檔案：
```properties
workspaceRoot=your/project/path
```

### 相依套件
主要相依套件包括：
- `fastmcp`：MCP 伺服器框架
- `requests`：HTTP 客戶端進行 API 呼叫
- `logging`：Python 內建日誌系統

## 📚 可用工具

### 公司資訊
- `get_company_profile(code)` - 公司基本資訊
- `get_company_dividend(code)` - 股利分配數據
- `get_company_monthly_revenue(code)` - 月營收報告

### 交易數據
- `get_stock_daily_trading(code)` - 每日交易統計
- `get_stock_monthly_average(code)` - 月平均價格
- `get_stock_valuation_ratios(code)` - 估值指標
- `get_stock_monthly_trading(code)` - 月交易數據
- `get_stock_yearly_trading(code)` - 年度交易統計

### 財務報表
- `get_company_income_statement(code)` - 綜合損益表
- `get_company_balance_sheet(code)` - 資產負債表數據

### 市場數據
- `get_market_index_info()` - 市場指數資訊
- `get_margin_trading_info()` - 融資融券統計

### ESG 與治理
- `get_company_governance_info(code)` - 公司治理
- `get_company_climate_management(code)` - 氣候相關管理
- `get_company_risk_management(code)` - 風險管理政策
- `get_company_supply_chain_management(code)` - 供應鏈數據
- `get_company_info_security(code)` - 資訊安全指標

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

## 📋 API 涵蓋範圍

目前支援 **15+ TWSE API 端點**，包括：
- 公司檔案和基本資訊
- 股票交易數據（每日、每月、每年）
- 財務報表和報告
- ESG 和永續指標
- 市場指數和統計
- 股利和治理資訊

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
- MCP 社群提供協議規範
- 本專案的貢獻者和使用者

## 📞 支援

- **問題回報**：[GitHub Issues](https://github.com/yourusername/TWStockMCPServer/issues)
- **討論區**：[GitHub Discussions](https://github.com/yourusername/TWStockMCPServer/discussions)
- **說明文件**：[Wiki](https://github.com/yourusername/TWStockMCPServer/wiki)

---

**以 ❤️ 為台灣股票分析社群打造**

