#!/usr/bin/env python
"""Quick test runner script for development."""

import sys
import subprocess

def run_tests(scope="all"):
    """Run tests based on scope."""
    commands = {
        "all": ["pytest", "tests/", "-v", "--tb=short"],
        "esg": ["pytest", "tests/e2e/test_esg_api.py", "-v"],
        "api": ["pytest", "tests/test_api_client.py", "-v"],
        "cov": ["pytest", "tests/", "-v", "--cov=tools", "--cov=utils", "--cov-report=html"],
        "quick": ["pytest", "tests/", "-x", "--tb=short"],  # Stop at first failure
    }
    
    if scope not in commands:
        print(f"Unknown scope: {scope}")
        print(f"Available scopes: {', '.join(commands.keys())}")
        return 1
    
    print(f"🧪 Running {scope} tests...\n")
    result = subprocess.run(commands[scope])
    
    if scope == "cov" and result.returncode == 0:
        print("\n📊 Coverage report generated in htmlcov/index.html")
    
    return result.returncode

if __name__ == "__main__":
    scope = sys.argv[1] if len(sys.argv) > 1 else "all"
    sys.exit(run_tests(scope))
