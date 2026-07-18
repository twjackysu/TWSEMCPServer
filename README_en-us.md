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

## 🧮 Advanced Features

### Futures & Options Positioning
Put/Call ratio, large-trader open interest, 三大法人 futures/options positions
> *"Is TX futures positioning bullish or bearish right now?" / "Where are large options traders positioned?"*

### Institutional Investor Flow
TWSE/OTC 三大法人 buy/sell, foreign investment by industry
> *"What are institutional investors buying today?" / "Which industry are foreign investors adding to?"*

### Company Fundamental Health Check
Profitability, growth, balance sheet, dividend policy, governance across five dimensions
> *"Give me a fundamental health check on TSMC" / "Is this company's financial health solid?"*

### Pre-Trade Risk Scan
Cross-checks disposal/warning/day-trading-restriction/margin-restriction lists
> *"Is this stock flagged for disposal or under a warning before I buy?"*

### Futures / Institutional Historical Lookback
openapi.taifex.com.tw only ever returns the latest trading day. This project additionally
scrapes TAIFEX's own website download pages (`www.taifex.com.tw`) for real historical data —
daily OHLC history for futures contracts, and 三大法人 futures position history
> *"Pull me a month of daily OHLC for TX futures" / "How has the foreign futures position changed over the last quarter?"*

## ⚙️ Quick Start

### 🚀 Online Usage (powered by [Prefect Horizon](https://horizon.prefect.io/))

This project is powered by **Prefect Horizon**, which hosts a free remote MCP Server:
```json
{
  "twstockmcpserver": {
    "transport": "streamable_http",
    "url": "https://TW-Stock-MCP-Server.fastmcp.app/mcp"
  }
}
```

> ⚠️ **Usage limit**: To keep the service sustainable, it has a fair-use ceiling (not unlimited). For **commercial use** or higher call volumes, we strongly recommend self-hosting via Docker / local install below, or a [Prefect Horizon](https://horizon.prefect.io/) paid plan.
>
> 🙏 Thanks to [Prefect Horizon](https://horizon.prefect.io/) for supporting this open-source project, making it easy for the community to try it out for free.

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
| [TWSE Web API](https://www.twse.com.tw) | TWSE web API endpoints — daily OHLC, monthly avg price, valuation, margin balance, listed stocks institutional investors (amounts/shares), whole-market daily close, TAIEX index history, foreign holdings history | 11 |
| [MIS Real-time Quotes](https://mis.twse.com.tw) | Intraday real-time multi-stock quotes (listed + OTC) | 1 |
| [TPEx OpenAPI](https://www.tpex.org.tw/openapi) | TPEx OTC market — daily close, institutional investors (per-stock/summary), P/E ratio, margin balance, warning/disposal stocks, ex-rights/dividends, odd-lot, index | 10 |
| [TAIFEX OpenAPI](https://openapi.taifex.com.tw) | TAIFEX derivatives — institutional series, large traders OI, daily market report, options analytics, margin, statistics | 16 |
| [TAIFEX website downloads](https://www.taifex.com.tw) | TAIFEX's own historical data-download pages — futures daily OHLC history, 三大法人 futures position history, Put/Call Ratio history, 三大法人 options calls/puts history, large-trader futures OI history, options daily OHLC history, 三大法人 futures+options total history, futures/options split history, options-by-contract history (openapi.taifex.com.tw only returns the latest trading day, no historical query support) | 9 |

## 🤝 Contributing
PRs welcome!

## 📄 License & Disclaimer
MIT License | For reference only, not investment advice