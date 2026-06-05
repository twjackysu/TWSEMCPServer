"""Decorators for error handling and common patterns."""

from functools import wraps
from typing import Callable, TypeVar, ParamSpec
import logging

from .constants import MSG_QUERY_FAILED

logger = logging.getLogger(__name__)

P = ParamSpec('P')
R = TypeVar('R')


def handle_api_errors(use_code_param: bool = False):
    """
    Decorator to handle common API errors and logging.

    Args:
        use_code_param: If True, expects the function to have a 'code' parameter
                       and includes it in error messages

    Usage:
        @handle_api_errors()
        def get_broker_info() -> str:
            ...

        @handle_api_errors(use_code_param=True)
        def get_stock_info(code: str) -> str:
            ...
    """
    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
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
