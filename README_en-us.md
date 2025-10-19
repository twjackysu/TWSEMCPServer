# 🚀 TWStockMCPServer

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![MCP](https://img.shields.io/badge/MCP-Compatible-green.svg)](https://modelcontextprotocol.io/)
[![API Tests](https://github.com/twjackysu/TWStockMCPServer/actions/workflows/api-tests.yml/badge.svg)](https://github.com/twjackysu/TWStockMCPServer/actions/workflows/api-tests.yml)

A comprehensive **Model Context Protocol (MCP) server** designed for Taiwan Stock Exchange (TWSE) data analysis, providing real-time stock information, financial statements, ESG data, and trend analysis functionality.

<a href="https://glama.ai/mcp/servers/@twjackysu/TWSEMCPServer">
  <img width="380" height="200" src="https://glama.ai/mcp/servers/@twjackysu/TWSEMCPServer/badge" />
</a>

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

## 📈 API Integration Progress

Current Progress: **38/143 (26.6%)** Completed ✅

Want to understand detailed API coverage? Check our **[API TODO List](API_TODO.md)** to track implementation progress!

> 💡 Run `python generate_todo.py` to automatically update progress statistics

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

### 🔧 Local Installation
```bash
git clone https://github.com/twjackysu/TWStockMCPServer.git
cd TWStockMCPServer
uv sync && uv run fastmcp dev server.py
```

## 🤝 Contributing
PRs welcome! Check the existing [API list](API_TODO.md) to understand expandable features.

## 📄 License & Disclaimer
MIT License | For reference only, not investment advice