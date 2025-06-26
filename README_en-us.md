# 🚀 TWStockMCPServer

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![MCP](https://img.shields.io/badge/MCP-Compatible-green.svg)](https://modelcontextprotocol.io/)

A comprehensive **Model Context Protocol (MCP) Server** for Taiwan Stock Exchange (TWSE) data analysis, providing real-time stock information, financial reports, ESG data, and trend analysis capabilities.

## � Demo

![Get stock trend demo](./staticFiles/sample-ezgif.com-resize.gif)

*Watch the demonstration of TWStockMCPServer in action*

## ✨ Features

### 📊 **Technical Analysis Tools**
- **Daily Trading Data**: Real-time stock prices, volumes, and trading statistics
- **Price Trends**: Daily closing prices and monthly average calculations
- **Valuation Metrics**: P/E ratios, dividend yields, and P/B ratios
- **Historical Data**: Monthly and yearly trading information

### 💰 **Fundamental Analysis**
- **Financial Statements**: Income statements and balance sheets
- **Revenue Reports**: Monthly revenue tracking and growth analysis
- **Dividend Information**: Distribution history and dividend policies
- **Corporate Governance**: ESG data and governance metrics

### 🏛️ **Market Intelligence**
- **Market Indices**: Real-time TWSE index information
- **Institutional Activity**: Margin trading and short selling data
- **Market Statistics**: Daily market summaries and trends

### 🌱 **ESG & Sustainability**
- **Climate Management**: Climate-related risk assessments
- **Risk Management**: Corporate risk management policies
- **Supply Chain**: Supply chain management transparency
- **Information Security**: Cybersecurity incident reporting

## �️ Installation

### Prerequisites
- Python 3.8 or higher
- pip package manager or [uv](https://github.com/astral-sh/uv)

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
   uv venv
   .venv\Scripts\activate  # Windows
   # or
   source .venv/bin/activate  # macOS/Linux
   uv add mcp[cli] httpx fastmcp requests
   ```

3. **Configure MCP Client**
   
   Add to your MCP client configuration (e.g., `.vscode/mcp.json`):
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

4. **Run the server**
   
   **Development Mode (with hot-reload):**
   ```bash
   uv run fastmcp dev server.py
   ```
   
   **Production Mode:**
   ```bash
   uv run fastmcp run server.py
   # or
   python server.py
   ```

## 🔧 Configuration

### Environment Variables
Create a `.env` file in the project root:
```properties
workspaceRoot=your/project/path
```

### Dependencies
Key dependencies include:
- `fastmcp`: MCP server framework
- `requests`: HTTP client for API calls
- `logging`: Built-in Python logging

## 📚 Available Tools

### Company Information
- `get_company_profile(code)` - Basic company information
- `get_company_dividend(code)` - Dividend distribution data
- `get_company_monthly_revenue(code)` - Monthly revenue reports

### Trading Data
- `get_stock_daily_trading(code)` - Daily trading statistics
- `get_stock_monthly_average(code)` - Monthly price averages
- `get_stock_valuation_ratios(code)` - Valuation metrics
- `get_stock_monthly_trading(code)` - Monthly trading data
- `get_stock_yearly_trading(code)` - Annual trading statistics

### Financial Reports
- `get_company_income_statement(code)` - Comprehensive income statements
- `get_company_balance_sheet(code)` - Balance sheet data

### Market Data
- `get_market_index_info()` - Market index information
- `get_margin_trading_info()` - Margin trading statistics

### ESG & Governance
- `get_company_governance_info(code)` - Corporate governance
- `get_company_climate_management(code)` - Climate-related management
- `get_company_risk_management(code)` - Risk management policies
- `get_company_supply_chain_management(code)` - Supply chain data
- `get_company_info_security(code)` - Information security metrics

## 💡 Usage Examples

### Basic Stock Analysis
```python
# Get Taiwan Semiconductor (2330) information
profile = get_company_profile("2330")
trading_data = get_stock_daily_trading("2330")
valuation = get_stock_valuation_ratios("2330")
```

### Trend Analysis
Use the built-in trend analysis prompt for comprehensive stock evaluation:
```python
# Analyze MediaTek's short-term prospects
analysis = stock_trend_analysis_prompt("2454", "short")
```

### ESG Analysis
```python
# Examine TSMC's ESG performance
governance = get_company_governance_info("2330")
climate = get_company_climate_management("2330")
risk_mgmt = get_company_risk_management("2330")
```

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

## 📋 API Coverage

Currently supports **15+ TWSE API endpoints** including:
- Company profiles and basic information
- Stock trading data (daily, monthly, yearly)
- Financial statements and reports
- ESG and sustainability metrics
- Market indices and statistics
- Dividend and governance information

## 🔒 Data Sources

All data is sourced from official Taiwan Stock Exchange (TWSE) OpenAPI:
- Base URL: `https://openapi.twse.com.tw/v1`
- Real-time and historical data
- No API key required
- Rate limiting applies

## ⚠️ Disclaimer

This software is for informational purposes only. It does not constitute financial advice. Users should conduct their own research and consult with financial professionals before making investment decisions.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Taiwan Stock Exchange for providing the open data API
- MCP community for the protocol specification
- Contributors and users of this project

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/TWStockMCPServer/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/TWStockMCPServer/discussions)
- **Documentation**: [Wiki](https://github.com/yourusername/TWStockMCPServer/wiki)

---

**Made with ❤️ for the Taiwan stock analysis community**

## 🌏 Language Versions

- **English** | [繁體中文](README.md)

> Disclaimer: As I am not familiar with Python, this project was entirely generated by AI and then manually adjusted as needed.
