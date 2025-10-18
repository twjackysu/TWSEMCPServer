#!/usr/bin/env python
"""Quick test runner script for development."""

import sys
import subprocess
import os
import webbrowser

def run_tests(scope="all"):
    """Run tests based on scope."""
    commands = {
        "all": ["pytest", "tests/", "-v", "--tb=short", "--maxfail=10"],
        "esg": ["pytest", "tests/e2e/test_esg_api.py", "-v"],
        "company": ["pytest", "tests/e2e/test_company_api.py", "-v"],
        "financials": ["pytest", "tests/e2e/test_financials_api.py", "-v"],
        "trading": ["pytest", "tests/e2e/test_trading_api.py", "-v"],
        "warrants": ["pytest", "tests/e2e/test_warrants_api.py", "-v"],
        "other": ["pytest", "tests/e2e/test_other_api.py", "-v"],
        "api": ["pytest", "tests/test_api_client.py", "-v"],
        "e2e": ["pytest", "tests/e2e/", "-v", "--tb=short"],  # All E2E tests
        "cov": ["pytest", "tests/", "-v", "--cov=tools", "--cov=utils", "--cov-report=html", "--cov-report=term"],
        "quick": ["pytest", "tests/", "-x", "--tb=short"],  # Stop at first failure
        "parallel": ["pytest", "tests/", "-v", "--tb=short", "-n", "auto", "--dist=worksteal"],  # Parallel execution
    }
    
    if scope not in commands:
        print(f"Unknown scope: {scope}")
        print(f"Available scopes: {', '.join(commands.keys())}")
        return 1
    
    print(f"🧪 Running {scope} tests...\n")

    # 使用 uv run 來執行 pytest
    cmd = ["uv", "run"] + commands[scope]
    result = subprocess.run(cmd)
    
    if scope == "cov" and result.returncode == 0:
        print("\n📊 Coverage report generated in htmlcov/index.html")
        # 自動開啟瀏覽器查看報告
        html_path = os.path.abspath("htmlcov/index.html")
        if os.path.exists(html_path):
            print(f"🌐 Opening coverage report in browser...")
            webbrowser.open(f"file://{html_path}")
    
    return result.returncode

if __name__ == "__main__":
    scope = sys.argv[1] if len(sys.argv) > 1 else "all"
    sys.exit(run_tests(scope))
