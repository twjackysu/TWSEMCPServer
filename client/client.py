import requests


class FastMCPClient:
    """Simple client for interacting with the FastMCP server."""

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    def initialize(self) -> dict:
        """Retrieve the list of available tools from the server."""
        url = f"{self.base_url}/initialize"
        response = requests.post(url, timeout=10)
        response.raise_for_status()
        return response.json()

    def query(self, tool_name: str, params: dict | None = None) -> dict:
        """Call a specific tool on the server."""
        url = f"{self.base_url}/query/{tool_name}"
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        return response.json()

