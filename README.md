# TWStockMCPServer

Simple MCP server built with **FastAPI** that exposes tools for querying the
[Taiwan Stock Exchange OpenAPI](https://openapi.twse.com.tw/).

This repository provides a starting point for building a FastMCP server. Each
tool wraps one of the TWSE endpoints and can be accessed through an HTTP
endpoint.

## Setup

Install dependencies:

```bash
pip install -r requirements.txt
```

## Running

Start the development server using `uvicorn`:

```bash
uvicorn server.main:app --reload
```

Then access `http://localhost:8000/query/{tool_name}` with optional query
parameters to call a specific tool.
