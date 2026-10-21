"""Decorators for error handling and common patterns."""

from functools import partial, wraps
from typing import Awaitable, Callable, TypeVar, ParamSpec
import logging

import anyio.to_thread
from fastmcp.exceptions import ToolError

from .constants import MSG_QUERY_FAILED

logger = logging.getLogger(__name__)

P = ParamSpec('P')
R = TypeVar('R')


def handle_api_errors(use_code_param: bool = False):
    """
    Decorator that makes a blocking tool function safe to serve and reports failures as MCP errors.

    - The tool body runs in a worker thread. FastMCP awaits tools on the event loop thread
      and calls a plain function right there, so a tool blocked on ``requests`` or on the
      client's throttle wait would stall every other request the server is handling.
    - Any exception becomes ``ToolError(MSG_QUERY_FAILED)``, which FastMCP returns with
      ``isError=true``. Returning the message as an ordinary string would tell the client
      the call succeeded. A ``ToolError`` raised by the tool itself passes through as is.

    Args:
        use_code_param: If True, expects the function to have a 'code' parameter
                       and includes it in error logs

    Usage:
        @handle_api_errors()
        def get_broker_info() -> str:
            ...

        @handle_api_errors(use_code_param=True)
        def get_stock_info(code: str) -> str:
            ...
    """
    def decorator(func: Callable[P, R]) -> Callable[P, Awaitable[R]]:
        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            try:
                return await anyio.to_thread.run_sync(partial(func, *args, **kwargs))
            except ToolError:
                raise
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

                raise ToolError(MSG_QUERY_FAILED.format(error=str(e))) from e

        return wrapper
    return decorator
