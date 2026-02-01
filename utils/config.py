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


class DisplayConfig:
    """Display and formatting configuration."""
    
    # Default number of records to display in list responses
    DEFAULT_DISPLAY_LIMIT: Final[int] = int(os.getenv(
        'DISPLAY_LIMIT',
        '20'
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
    'DisplayConfig',
    'TestConfig',
]
