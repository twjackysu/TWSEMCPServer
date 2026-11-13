"""Configuration management for TWStockMCPServer.

This module centralizes all configuration values and supports environment variable overrides.
"""

import os
from typing import Final


class APIConfig:
    """TWSE API configuration settings."""
    
    # API Base URL
    BASE_URL: Final[str] = os.getenv(
        'TWSE_API_BASE_URL',
        'https://openapi.twse.com.tw/v1'
    )
    
    # User Agent for API requests
    USER_AGENT: Final[str] = os.getenv(
        'TWSE_USER_AGENT',
        'stock-mcp/1.0'
    )
    
    # Minimum interval between API requests (seconds) to avoid rate limiting
    REQUEST_INTERVAL: Final[float] = float(os.getenv(
        'TWSE_REQUEST_INTERVAL',
        '0.5'
    ))
    
    # Default timeout for API requests (seconds)
    DEFAULT_TIMEOUT: Final[float] = float(os.getenv(
        'TWSE_API_TIMEOUT',
        '30.0'
    ))
    
    # SSL verification (set to False for TWSE API due to certificate issues)
    VERIFY_SSL: Final[bool] = os.getenv(
        'TWSE_VERIFY_SSL',
        'false'
    ).lower() in ('true', '1', 'yes')

    # TTL (seconds) for the in-memory OpenAPI list-response cache in TWSEAPIClient.fetch_data.
    # A single prompt often triggers several tools that hit the same endpoint (e.g. multiple
    # company-lookup tools reading the same full company list) within seconds of each other;
    # this avoids re-downloading the whole list for each one. Set to 0 to disable caching.
    CACHE_TTL: Final[float] = float(os.getenv(
        'TWSE_CACHE_TTL',
        '60'
    ))

    # Upper bound on entries in the per-call response cache used by fetch_json / fetch_bytes
    # when a tool passes ``cache_ttl``. Keys include query parameters, so without a bound a
    # long-running server would keep one entry per distinct query forever.
    RESPONSE_CACHE_MAX_ENTRIES: Final[int] = int(os.getenv(
        'TWSE_RESPONSE_CACHE_MAX_ENTRIES',
        '256'
    ))


class BranchDBConfig:
    """Neon PostgreSQL 分點進出資料庫設定。

    查詢工具用 ``URL``（建議指向唯讀 role），只有回填工具用 ``WRITE_URL``；
    ``WRITE_URL`` 未設定時退回 ``URL``。兩者皆未設定時工具照常註冊，但呼叫
    會回 MSG_BRANCH_DB_NOT_CONFIGURED，不會讓 server 啟動失敗。
    """

    URL: Final[str] = os.getenv('BRANCH_DB_URL', '')

    WRITE_URL: Final[str] = os.getenv('BRANCH_DB_WRITE_URL', '')

    # 過去交易日的分點資料不會再變動，所以查詢結果可以放心快取
    CACHE_TTL: Final[float] = float(os.getenv('BRANCH_DB_CACHE_TTL', '300'))

    # 連線 / 查詢 timeout（秒）。Neon 的 compute 冷啟動會讓第一次連線變慢
    TIMEOUT: Final[float] = float(os.getenv('BRANCH_DB_TIMEOUT', '15'))

    # 單次查詢回傳列數硬上限，避免一次把整張明細表讀進記憶體
    MAX_ROWS: Final[int] = int(os.getenv('BRANCH_DB_MAX_ROWS', '5000'))


class DisplayConfig:
    """Display and formatting configuration."""
    
    # Default number of records to display in list responses
    DEFAULT_DISPLAY_LIMIT: Final[int] = int(os.getenv(
        'DISPLAY_LIMIT',
        '50'
    ))
    
    # Maximum number of records for holiday schedule
    HOLIDAY_DISPLAY_LIMIT: Final[int] = int(os.getenv(
        'HOLIDAY_DISPLAY_LIMIT',
        '50'
    ))


class TestConfig:
    """Test-specific configuration."""
    
    # Delay between test requests (seconds)
    TEST_DELAY: Final[float] = float(os.getenv(
        'PYTEST_DELAY_SECONDS',
        '1.0'
    ))


# Convenience exports
__all__ = [
    'APIConfig',
    'BranchDBConfig',
    'DisplayConfig',
    'TestConfig',
]
