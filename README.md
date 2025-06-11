# Taiwan Stock Exchange MCP Server 🏆

A Model Context Protocol (MCP) server that provides access to Taiwan Stock Exchange (TWSE) OpenAPI data for stock analysis and company information retrieval.

## 🚀 Features

- **Company Profile Lookup**: Get detailed information for any listed Taiwan company by stock code
- **Stock Trend Analysis**: AI-powered prompts for technical, fundamental, and chip analysis
- **Multi-timeframe Analysis**: Support for short, medium, and long-term trend analysis
- **Real-time Data**: Direct integration with TWSE OpenAPI endpoints
- **Comprehensive Logging**: Built-in logging for debugging and monitoring

## 📋 Prerequisites

- Python 3.13 or higher
- [uv](https://github.com/astral-sh/uv) package manager

## 🛠️ Installation

### 1. Create and activate virtual environment
```
uv venv
.venv\Scripts\activate  # Windows
# or
source .venv/bin/activate  # macOS/Linux
```

### 2. Install dependencies
```
uv add mcp[cli] httpx fastmcp requests
```

### 🚀 Usage
Development Mode
For development with hot-reload:

```
uv run fastmcp dev server.py
```

Production Mode
For production deployment:
```
uv run fastmcp run server.py
```
