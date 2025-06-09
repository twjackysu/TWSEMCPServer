# TWStockMCPServer

This project demonstrates a simple MCP server built with **FastMCP**. It exposes tools for querying the [Taiwan Stock Exchange OpenAPI](https://openapi.twse.com.tw/).

## 1. Setup

Install the required packages:

```bash
pip install -r requirements.txt
```

## 2. Running the Server

Start the development server with `uvicorn`:

```bash
uvicorn server.main:app --reload
```

When the server is running you can discover the available tools:

```bash
curl -X POST http://localhost:8000/initialize
```

Use `/query/{tool_name}` with optional parameters to fetch data. For example:

```bash
curl "http://localhost:8000/query/all_stocks?date=20240101"
```

## 3. Using the Python Client

The `client/client.py` module provides `FastMCPClient` for programmatic access.

```python
from client.client import FastMCPClient

client = FastMCPClient("http://localhost:8000")
print(client.initialize())
print(client.query("all_stocks", params={"date": "20240101"}))
```

You can also use the command line interface:

```bash
python -m client --list-tools
python -m client all_stocks --param date=20240101
```

## OpenAPI Document

For reference, `openapi/openapi.yaml` describes the TWSE endpoints used by this server.
