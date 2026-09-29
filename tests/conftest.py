"""Pytest configuration and shared fixtures."""

import pytest
import logging
import time
import requests
from utils.config import TestConfig, APIConfig

# 設定測試日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)

# 使用集中管理的配置
TEST_DELAY = TestConfig.TEST_DELAY


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
    return APIConfig.DEFAULT_TIMEOUT

def pytest_configure(config):
    config.addinivalue_line(
        "markers", "offline: 不打網路的 unit test，不需要 rate limit 延遲"
    )


@pytest.fixture(autouse=True)
def block_network_in_offline_tests(request, monkeypatch):
    """offline 測試一碰到真實 HTTP 就失敗，而不是悄悄連上外部 API."""
    if not request.node.get_closest_marker("offline"):
        return

    def _refuse(self, method, url, *args, **kwargs):
        raise AssertionError(f"offline 測試不得發出真實 HTTP 請求: {method} {url}")

    monkeypatch.setattr(requests.Session, "request", _refuse)


@pytest.fixture(autouse=True)
def rate_limit_delay(request):
    """每個測試之間自動延遲，避免被視為 DDOS 攻擊."""
    yield
    if request.node.get_closest_marker("offline"):
        return
    # 測試執行後延遲，時間可透過環境變數 PYTEST_DELAY_SECONDS 設定
    if TEST_DELAY > 0:
        logging.info(f"Rate limiting: waiting {TEST_DELAY} seconds before next test")
        time.sleep(TEST_DELAY)
