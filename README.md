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

To check the available tools programmatically, first call the `/initialize`
endpoint:

```bash
curl -X POST http://localhost:8000/initialize
```

This returns a JSON object listing the supported tool names.

## Using the FastMCP Client

A minimal client implementation is included in `client/client.py`. You can use
it to interact with the server programmatically:

```python
from client.client import FastMCPClient

client = FastMCPClient("http://localhost:8000")

# Discover available tools
print(client.initialize())

# Call a specific tool
result = client.query("all_stocks", params={"date": "20240101"})
print(result)
```

Alternatively you can run the client from the command line. This requires the
server to be running first:

```bash
# List the available tools
python -m client --list-tools

# Query a specific tool with optional parameters
python -m client all_stocks --param date=20240101
```

