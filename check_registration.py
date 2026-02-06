
import sys
import logging
from unittest.mock import MagicMock

# Setup logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Mock FastMCP
class MockFastMCP:
    def __init__(self, name):
        self.name = name
    def tool(self, func):
        print(f"[SUCCESS] Registered tool: {func.__name__}")
        return func
    def prompt(self, func):
        return func

# Mock dependencies
sys.modules['fastmcp'] = MagicMock()
sys.modules['fastmcp'].FastMCP = MockFastMCP

# Import our code
try:
    from tools import register_all_tools
    from utils.api_client import TWSEAPIClient
    
    print("--- Starting Registration Check ---")
    mcp = MockFastMCP("TestServer")
    client = TWSEAPIClient.get_instance()
    
    register_all_tools(mcp, client)
    print("--- Registration Check Complete ---")
    
except Exception as e:
    print(f"FATAL ERROR: {e}")
    import traceback
    traceback.print_exc()
