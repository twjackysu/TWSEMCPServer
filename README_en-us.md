# 🚀 TWStockMCPServer

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![MCP](https://img.shields.io/badge/MCP-Compatible-green.svg)](https://modelcontextprotocol.io/)
[![API Tests](https://github.com/twjackysu/TWStockMCPServer/actions/workflows/api-tests.yml/badge.svg)](https://github.com/twjackysu/TWStockMCPServer/actions/workflows/api-tests.yml)

A comprehensive **Model Context Protocol (MCP) server** designed for Taiwan Stock Exchange (TWSE) data analysis, providing real-time stock information, financial statements, ESG data, and trend analysis functionality.


## 🌏 Language Versions

- **English** | [繁體中文](README.md)

## 🎬 Demo

### VSCode Copilot demo
![VSCode Copilot demo](./staticFiles/sample-ezgif.com-resize.gif)

### Gemini CLI demo
![Gemini CLI demo](./staticFiles/gemini-cli-demo.gif)

*Watch TWStockMCPServer in action*

## ✨ Five Investment Analysis Scenarios

### 📊 **Individual Stock Trend Analysis**
Comprehensive analysis combining technical, fundamental, and institutional trading perspectives
> *"Analyze TSMC (2330) recent trends" / "Is Hon Hai (2317) suitable for long-term investment?"*

### 💰 **Foreign Investment Insights**
Foreign holdings, industry flows, and individual stock entry/exit tracking
> *"What stocks are foreign investors buying recently?" / "How are foreign investment trends in semiconductors?"*

### 🔥 **Market Hotspot Detection**
Major announcements, abnormal trading volumes, warrant activity monitoring
> *"What major news happened today?" / "Which stocks have abnormal trading volumes?"*

### 💎 **Dividend Investment Planning**
High-yield screening, ex-dividend calendar, payout stability analysis
> *"Recommend some high-yield stocks" / "Which companies go ex-dividend next month?"*

### 🎯 **Investment Screening**
Value/growth stock selection, ESG risk assessment
> *"Help me find some undervalued stocks" / "Which companies have good ESG performance?"*

## ⚙️ Quick Start

### 🚀 Online Usage (Recommended)
```json
{
  "twstockmcpserver": {
    "transport": "streamable_http",
    "url": "https://TW-Stock-MCP-Server.fastmcp.app/mcp"
  }
}
```

### 🐳 Docker (stdio)
```json
{
  "twstockmcpserver": {
    "command": "docker",
    "args": [
      "run",
      "-i",
      "--rm",
      "--pull=always",
      "-e",
      "MCP_STDIO=1",
      "ghcr.io/twjackysu/twsemcpserver:latest"
    ]
  }
}
```

### 🔧 Local Installation
```bash
git clone https://github.com/twjackysu/TWStockMCPServer.git
cd TWStockMCPServer
uv sync && uv run fastmcp dev server.py
```

## 📡 Data Sources

| Source | Description | Tools |
|--------|-------------|-------|
| [TWSE OpenAPI](https://openapi.twse.com.tw) | Taiwan Stock Exchange official API — corporate governance, ESG, financials, trading, indices, etc. | 143 |
| [TWSE Web API](https://www.twse.com.tw) | TWSE web API endpoints — daily OHLC, monthly avg price, valuation, margin balance, listed stocks institutional investors | 6 |
| [MIS Real-time Quotes](https://mis.twse.com.tw) | Intraday real-time multi-stock quotes (listed + OTC) | 1 |
| [TPEx OpenAPI](https://www.tpex.org.tw/openapi) | TPEx OTC market — daily close, institutional investors (per-stock/summary), P/E ratio, margin balance, warning/disposal stocks, ex-rights/dividends, odd-lot, index | 10 |
| [TAIFEX OpenAPI](https://openapi.taifex.com.tw) | TAIFEX derivatives — institutional series, large traders OI, daily market report, options analytics, margin, statistics | 16 |

## 🤝 Contributing
PRs welcome!

## 📄 License & Disclaimer
MIT License | For reference only, not investment advice