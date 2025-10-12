# 🚀 TWStockMCPServer

[![License: MIT](https://## ⚙️ Installation

### 🚀 Option 1: Direct Online Usage (Recommended)

Thanks to FastMCP Cloud for providing free hosting service (temporarily free), you can directly use the following configuration to connect to our MCP server:

```json
{
  "twstockmcpserver": {
    "transport": "streamable_http",
    "url": "https://TW-Stock-MCP-Server.fastmcp.app/mcp"
  }
}
```

### 🔧 Option 2: Local Installation

#### Prerequisites
- Python 3.13 or higher
- pip package manager or [uv](https://github.com/astral-sh/uv) (recommended)

#### Quick Startelds.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![MCP](https://img.shields.io/badge/MCP-Compatible-green.svg)](https://modelcontextprotocol.io/)

A comprehensive **Model Context Protocol (MCP) Server** for Taiwan Stock Exchange (TWSE) data analysis, providing real-time stock information, financial reports, ESG data, and trend analysis capabilities.

<a href="https://glama.ai/mcp/servers/@twjackysu/TWSEMCPServer">
  <img width="380" height="200" src="https://glama.ai/mcp/servers/@twjackysu/TWSEMCPServer/badge" />
</a>

## 🌏 Language Versions

- **English** | [繁體中文](README.md)

## � Demo

### VSCode Copilot demo
![VSCode Copilot demo](./staticFiles/sample-ezgif.com-resize.gif)

### Gemini CLI demo
![Gemini CLI demo](./staticFiles/gemini-cli-demo.gif)

*Watch the demonstration of TWStockMCPServer in action*

## ✨ Features

### 📊 **Technical Analysis Tools**
- **Daily Trading Data**: Real-time stock prices, volumes, and trading statistics
- **Price Trends**: Daily closing prices and monthly average calculations
- **Valuation Metrics**: P/E ratios, dividend yields, and P/B ratios
- **Historical Data**: Monthly and yearly trading information
- **Real-time Statistics**: 5-second interval trading statistics

### 💰 **Fundamental Analysis**
- **Financial Statements**: Income statements and balance sheets (general industry)
- **Revenue Reports**: Monthly revenue tracking and growth analysis
- **Dividend Information**: Distribution history and dividend policies
- **Corporate Governance**: ESG data and governance metrics

### 🏛️ **Market Intelligence**
- **Market Indices**: Real-time TWSE index information and historical data
- **Institutional Activity**: Margin trading and short selling data
- **Market Statistics**: Daily market summaries and long-term trend analysis

### 🌱 **ESG & Sustainability**
- **Climate Management**: Climate-related risk assessments
- **Risk Management**: Corporate risk management policies
- **Supply Chain**: Supply chain management transparency
- **Information Security**: Cybersecurity incident reporting

## 📈 API Implementation Progress

Want to see our current API coverage? Check out our **[API TODO List](API_TODO.md)** to track implementation progress!

Current Progress: **35/143 (24.5%)** Completed ✅

- Corporate Governance: 8/56 (14.3%)
- Securities Trading: 12/36 (33.3%)
- Financial Statements: 9/30 (30%)
- Warrants: 2/3 (66.7%)
- Other categories in progress...

> 💡 **Update Progress**: Run `python generate_todo.py` to auto-scan and update implementation status

## ⚙️ Installation

### Prerequisites
- Python 3.13 or higher
- pip package manager or [uv](https://github.com/astral-sh/uv) (recommended)

### Quick Start

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/TWStockMCPServer.git
   cd TWStockMCPServer
   ```

2. **Install dependencies**
   
   **Using pip:**
   ```bash
   pip install -r requirements.txt
   ```
   
   **Using uv (recommended):**
   ```bash
   uv sync
   ```

3. **Run the server**
   
   **Development Mode (with hot-reload):**
   ```bash
   uv run fastmcp dev server.py
   ```
   
   **Production Mode:**
   ```bash
   uv run fastmcp run server.py
   ```

## 🎯 Five Core Question Scenarios

### 1. **Stock Trend Analysis** (`stock_trend_analysis_prompt`)
**Questions you can ask:**
- "Please analyze the short-term trend of TSMC (2330)"
- "How is the medium-term trend of Evergreen (2603)?"
- "Long-term investment value analysis of Hon Hai (2317)"

**Using tools:** 15 tools covering technical, fundamental, chip, news, and ESG analysis

### 2. **Foreign Investment Analysis** (`foreign_investment_analysis`)
**Questions you can ask:**
- "Which industries do foreign investors prefer most?"
- "What are the current top 20 companies by foreign holdings?"
- "How is MediaTek's (2454) foreign investment status?"
- "Semiconductor industry foreign investment trend analysis"

**Using tools:** 6 tools focused on foreign investment flows and fundamental validation

### 3. **Market Hotspot Monitoring** (`market_hotspot_monitoring`)
**Questions you can ask:**
- "What major news is in the market today?"
- "Which stocks have abnormally active trading volumes?"
- "What important ex-dividend schedules are there this week?"
- "How is the current market speculation sentiment?"

**Using tools:** 8 tools monitoring news, trading activity, and corporate actions

### 4. **Dividend Investment Strategy** (`dividend_investment_strategy`)
**Questions you can ask:**
- "Recommend some high dividend yield stocks"
- "Which companies will go ex-dividend next quarter?"
- "Dividend growth portfolio recommendations"
- "Financial sector dividend investment opportunities analysis"

**Using tools:** 9 tools focused on dividend analysis and financial assessment

### 5. **Investment Screening** (`investment_screening`)
**Questions you can ask:**
- "Recommend some value investment targets"
- "Growth stock screening criteria and recommendations"
- "Stocks suitable for conservative investors"
- "Which stocks are currently favored by foreign investors?"

**Using tools:** 12 tools for comprehensive screening and risk assessment

## 📚 Available Tools

### Company Information (13 tools)
**Basic Information & News:**
- `get_company_profile(code)` - Basic company information
- `get_company_dividend(code)` - Dividend distribution data
- `get_company_monthly_revenue(code)` - Monthly revenue reports
- `get_company_major_news(code)` - Company major announcements
- `get_twse_news(start_date, end_date)` - TWSE official news (with optional date filtering)
- `get_twse_events(top=10)` - TWSE event announcements

**Financial Reports:**
- `get_company_income_statement(code)` - Comprehensive income statements (general industry)
- `get_company_balance_sheet(code)` - Balance sheet data (general industry)

**ESG & Governance:**
- `get_company_governance_info(code)` - Corporate governance
- `get_company_climate_management(code)` - Climate-related management
- `get_company_risk_management(code)` - Risk management policies
- `get_company_supply_chain_management(code)` - Supply chain data
- `get_company_info_security(code)` - Information security metrics

### Trading Data (10 tools)
- `get_stock_daily_trading(code)` - Daily trading statistics
- `get_stock_monthly_average(code)` - Monthly price averages
- `get_stock_valuation_ratios(code)` - Valuation metrics (P/E, dividend yield, P/B ratios)
- `get_stock_monthly_trading(code)` - Monthly trading data
- `get_stock_yearly_trading(code)` - Annual trading statistics
- `get_dividend_rights_schedule(code)` - Ex-dividend/rights schedule
- `get_etf_regular_investment_ranking()` - ETF regular investment ranking
- `get_warrant_basic_info(code)` - Warrant basic information
- `get_warrant_daily_trading(code)` - Warrant daily trading data
- `get_warrant_trader_count()` - Warrant daily trader count

### Market Data (6 tools)
- `get_market_index_info(category, count, format)` - Market index information (with category filtering, count control, and format selection)
  - **category**: Index category (major=major indices, sector=industry sectors, esg=ESG indices, leverage=leveraged indices, return=total return indices, thematic=themed indices, dividend=high dividend indices, all=all indices)
  - **count**: Number of results to return (default: 20, max: 50)
  - **format**: Output format (detailed=full details, summary=compact summary, simple=name and change only)
- `get_margin_trading_info()` - Margin trading statistics
- `get_real_time_trading_stats()` - Real-time trading statistics (5-second updates)
- `get_market_historical_index()` - Taiwan Capitalization Weighted Stock Index historical data
- `get_foreign_investment_by_industry()` - Foreign and mainland China investment by industry
- `get_top_foreign_holdings()` - Top 20 foreign and mainland China holdings

## 🤝 Contributing

We welcome contributions from the developer community! Here's how you can help:

### Ways to Contribute

1. **Add New Tools**: Extend the API coverage by implementing new TWSE endpoints
2. **Improve Documentation**: Help improve examples and documentation
3. **Bug Fixes**: Report and fix issues
4. **Feature Requests**: Suggest new functionality
5. **Testing**: Add test cases and improve reliability

### Development Setup

1. **Fork the repository**
2. **Create a feature branch**
   ```bash
   git checkout -b feature/your-new-tool
   ```
3. **Add your tool to `server.py`**
   ```python
   @mcp.tool
   def your_new_tool(code: str) -> str:
       """Your tool description."""
       # Implementation here
   ```
4. **Update documentation**
5. **Submit a pull request**

### API Reference
Refer to `staticFiles/apis_summary_simple.json` for available TWSE API endpoints that can be implemented as new tools.

### Code Style
- Follow Python PEP 8 guidelines
- Add comprehensive docstrings
- Include error handling
- Log important operations

## 🔒 Data Sources

All data is sourced from official Taiwan Stock Exchange (TWSE) OpenAPI:
- Base URL: `https://openapi.twse.com.tw/v1`
- Real-time and historical data
- No API key required
- Rate limiting applies

## ⚠️ Disclaimer

This software is for informational purposes only. It does not constitute financial advice. Users should conduct their own research and consult with financial professionals before making investment decisions. As I am not familiar with Python, this project was entirely generated by AI and then manually adjusted as needed.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Taiwan Stock Exchange for providing the open data API
- [FastMCPCloud](https://fastmcp.app/) for providing free MCP server hosting service
- MCP community for the protocol specification
- Contributors and users of this project

---

**Made with ❤️ for the Taiwan stock analysis community**

