"""Pytest configuration and shared fixtures."""

import pytest
import logging
import time
import os

# 設定測試日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)

# 從環境變數讀取延遲時間，預設為 1 秒
# 在 CI 環境中可以設定更長的延遲時間
TEST_DELAY = float(os.getenv('PYTEST_DELAY_SECONDS', '1.0'))

@pytest.fixture
def sample_stock_code():
    """提供測試用的股票代號（台積電）."""
    return "2330"

@pytest.fixture
def sample_stock_code_with_data():
    """提供有訴訟損失資料的股票代號（大成）."""
    return "1210"

@pytest.fixture(scope="session")
def api_timeout():
    """API 請求超時時間."""
    return 30.0

@pytest.fixture(autouse=True)
def rate_limit_delay():
    """每個測試之間自動延遲，避免被視為 DDOS 攻擊."""
    yield
    # 測試執行後延遲，時間可透過環境變數 PYTEST_DELAY_SECONDS 設定
    if TEST_DELAY > 0:
        logging.info(f"Rate limiting: waiting {TEST_DELAY} seconds before next test")
        time.sleep(TEST_DELAY)
