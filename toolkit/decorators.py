"""Decorators for error handling and common patterns."""

from functools import wraps
from typing import Callable, TypeVar, ParamSpec
import logging

from fastmcp.exceptions import ToolError

from utils.constants import MSG_QUERY_FAILED
from utils.errors import InvalidArgument

logger = logging.getLogger(__name__)

P = ParamSpec('P')
R = TypeVar('R')


def handle_api_errors(use_code_param: bool = False):
    """
    Decorator that reports a tool's failures as MCP errors with the localized message.

    Any exception becomes ``ToolError(MSG_QUERY_FAILED)``, which FastMCP returns with
    ``isError=true``. Returning the message as an ordinary string would tell the client the
    call succeeded, and leaving the exception to FastMCP would give the client its English
    ``Error calling tool …`` text instead. A ``ToolError`` raised by the tool itself passes
    through as is, and ``utils.errors.InvalidArgument`` (a bad argument noticed in utils/, e.g. by
    ``Page``) becomes a ``ToolError`` with its own message.

    The tool stays a plain function: FastMCP 4 runs sync tools in a worker thread, so one
    blocked on ``requests`` or on the client's throttle wait does not stall the server.

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
    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            try:
                return func(*args, **kwargs)
            except ToolError:
                raise
            except InvalidArgument as e:
                # The caller's argument, raised from utils/ (which cannot import ToolError)
                raise ToolError(str(e)) from e
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
