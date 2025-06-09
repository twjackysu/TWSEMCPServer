import requests
import urllib3

# Disable SSL warnings - Not recommended for production
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class TWSETool:
    """Simple wrapper for TWSE OpenAPI endpoints."""

    BASE_URL = "https://openapi.twse.com.tw"

    def __init__(self, endpoint: str):
        self.endpoint = endpoint

    def query(self, params=None):
        url = f"{self.BASE_URL}{self.endpoint}"
        response = requests.get(url, params=params, timeout=10, verify=False)
        response.raise_for_status()
        return response.json()
