"""Pytest configuration and shared fixtures."""

import pytest
import logging

# 設定測試日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)

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
