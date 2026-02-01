"""Decorators for error handling and common patterns."""

from functools import wraps
from typing import Callable, Any
import logging

from .constants import MSG_QUERY_FAILED, MSG_NO_DATA

logger = logging.getLogger(__name__)


def handle_api_errors(data_type: str = "", use_code_param: bool = False):
    """
    Decorator to handle common API errors and logging.
    
    Args:
        data_type: Type of data being queried (e.g., "券商資料")
        use_code_param: If True, expects the function to have a 'code' parameter
                       and includes it in error messages
    
    Usage:
        @handle_api_errors(data_type="券商資料")
        def get_broker_info() -> str:
            ...
            
        @handle_api_errors(use_code_param=True)
        def get_stock_info(code: str) -> str:
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # Extract code parameter if it exists
                code = None
                if use_code_param:
                    # Try to get 'code' from kwargs or first positional arg
                    code = kwargs.get('code')
                    if code is None and len(args) > 0:
                        code = args[0]
                
                # Log the error with context
                error_context = f" for code {code}" if code else ""
                logger.error(f"Error in {func.__name__}{error_context}: {e}", exc_info=True)
                
                # Return formatted error message
                return MSG_QUERY_FAILED.format(error=str(e))
        
        return wrapper
    return decorator


def handle_empty_response(data_type: str):
    """
    Decorator to handle empty API responses.
    
    This should be used in conjunction with handle_api_errors.
    
    Args:
        data_type: Type of data for the error message (e.g., "券商資料")
    
    Usage:
        @handle_empty_response(data_type="券商資料")
        @handle_api_errors()
        def get_broker_info() -> str:
            data = fetch_data()
            if not data:
                return None  # Will be caught by decorator
            return format_data(data)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            result = func(*args, **kwargs)
            if result is None or result == "":
                return MSG_NO_DATA.format(data_type=data_type)
            return result
        
        return wrapper
    return decorator
