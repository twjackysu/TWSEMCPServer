# 🚀 TWStockMCPServer

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![MCP](https://img.shields.io/badge/MCP-Compatible-green.svg)](https://modelcontextprotocol.io/)
[![API Tests](https://github.com/twjackysu/TWStockMCPServer/actions/workflows/api-tests.yml/badge.svg)](https://github.com/twjackysu/TWStockMCPServer/actions/workflows/api-tests.yml)

一個全面的**模型上下文協議 (MCP) 伺服器**，專為台灣證券交易所 (TWSE) 數據分析設計，提供即時股票資訊、財務報表、ESG 數據和趨勢分析功能。

<a href="https://glama.ai/mcp/servers/@twjackysu/TWSEMCPServer">
  <img width="380" height="200" src="https://glama.ai/mcp/servers/@twjackysu/TWSEMCPServer/badge" />
</a>

## 🌏 語言版本

- [English](README_en-us.md) | **繁體中文**

## 🎬 示範影片

### VSCode Copilot demo
![VSCode Copilot demo](./staticFiles/sample-ezgif.com-resize.gif)

### Gemini CLI demo
![Gemini CLI demo](./staticFiles/gemini-cli-demo.gif)

*觀看 TWStockMCPServer 功能展示*

## ✨ 五大投資分析情境

### 📊 **個股趨勢研判**
短中長期技術面、基本面、籌碼面綜合分析
> *"分析台積電(2330)最近的走勢" / "鴻海(2317)適合長期投資嗎？"*

### 💰 **外資投資解讀**
外資持股、產業流向、個股進出追蹤
> *"外資最近在買什麼股票？" / "半導體業外資投資趨勢如何？"*

### 🔥 **市場熱點捕捉**
重大訊息、異常成交、權證活躍度監控
> *"今天有什麼重大消息？" / "哪些股票交易量異常活躍？"*

### 💎 **股利投資規劃**
高殖利率篩選、除權息行事曆、配息穩定性分析
> *"推薦一些高殖利率股票" / "下個月有哪些公司要除權息？"*

### 🎯 **投資標的篩選**
價值股/成長股篩選、ESG風險評估
> *"幫我找一些被低估的價值股" / "ESG表現好的公司有哪些？"*

## ⚙️ 快速開始

### 🚀 線上使用（推薦）
```json
{
  "twstockmcpserver": {
    "transport": "streamable_http",
    "url": "https://TW-Stock-MCP-Server.fastmcp.app/mcp"
  }
}
```

### 🔧 本地安裝
```bash
git clone https://github.com/twjackysu/TWStockMCPServer.git
cd TWStockMCPServer
uv sync && uv run fastmcp dev server.py
```

## 📡 資料來源

| 來源 | 說明 | Tools |
|------|------|-------|
| [TWSE OpenAPI](https://openapi.twse.com.tw) | 台灣證交所官方 API — 公司治理、ESG、財報、交易、指數等 | 143 個 |
| [TWSE exchangeReport](https://www.twse.com.tw) | 證交所歷史行情 — 個股日K、月均價、估值、融資融券 | 4 個 |
| [MIS 即時報價](https://mis.twse.com.tw) | 盤中即時多股報價（上市+上櫃） | 1 個 |
| [TPEx OpenAPI](https://www.tpex.org.tw/openapi) | 櫃買中心 — 上櫃日收盤、三大法人、本益比 | 3 個 |
| [TAIFEX OpenAPI](https://openapi.taifex.com.tw) | 期交所 — 三大法人期貨部位、Put/Call Ratio | 2 個 |

## 🤝 參與貢獻
歡迎PR！

## 📄 授權 & 免責聲明
MIT授權 | 僅供參考，不構成投資建議

