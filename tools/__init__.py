"""MCP tools for TWStockMCPServer."""

import importlib
import inspect
import pkgutil
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, List, Optional

if TYPE_CHECKING:
    from fastmcp import FastMCP
    from utils.api_client import TWSEAPIClient

logger = logging.getLogger(__name__)


class ToolRegistrar:
    """The ``mcp`` every ``register_tools(mcp, client)`` receives: ``mcp.tool`` with server-wide defaults.

    Tool modules only call ``mcp.tool`` (bare, with keywords, or ``mcp.tool(name=...)(fn)``), and
    this forwards each call to FastMCP, adding defaults that should hold for every tool:

    - ``output_schema=None`` for a tool whose return type is ``str``. FastMCP 4 would otherwise
      give it a ``{"result": string}`` output schema and send the text twice per call, in
      ``content`` and again in ``structuredContent``.

    A keyword the tool passes itself always wins.
    """

    def __init__(self, mcp: "FastMCP"):
        self._mcp = mcp

    def tool(self, name_or_fn: Any = None, **kwargs: Any) -> Any:
        if callable(name_or_fn):
            return self._register(name_or_fn, None, kwargs)
        return lambda fn: self._register(fn, name_or_fn, kwargs)

    def _register(self, fn: Callable[..., Any], name: Optional[str], kwargs: dict) -> Any:
        if inspect.signature(fn, eval_str=True).return_annotation is str:
            kwargs = {"output_schema": None, **kwargs}
        if name is not None:  # mcp.tool("custom_name")
            kwargs = {"name": name, **kwargs}
        return self._mcp.tool(fn, **kwargs)


def discover_tool_modules() -> List[str]:
    """Dotted names of every tool module: ``tools/*.py`` and ``tools/<package>/*.py``, sorted."""
    tools_package = Path(__file__).parent.resolve()  # Use absolute path
    logger.info(f"Scanning tools in: {tools_package}")

    modules = []
    for module_info in pkgutil.iter_modules([str(tools_package)]):
        if not module_info.ispkg:
            modules.append(f"tools.{module_info.name}")
            continue
        subpackage_path = tools_package / module_info.name
        for sub_info in pkgutil.iter_modules([str(subpackage_path)]):
            if not sub_info.ispkg:
                modules.append(f"tools.{module_info.name}.{sub_info.name}")
    return sorted(modules)


def register_all_tools(mcp: "FastMCP", client: Optional["TWSEAPIClient"] = None) -> None:
    """
    Automatically discover and register all MCP tools from submodules.

    Fails fast: a module that cannot be imported, lacks ``register_tools`` or raises while
    registering stops the server from starting. Logging and carrying on would start a
    server that silently lacks that module's tools.

    Modules register through a ``ToolRegistrar`` around ``mcp``, which applies the server-wide
    tool defaults.

    Args:
        mcp: FastMCP instance to register tools with
        client: TWSEAPIClient instance for dependency injection
    """
    modules = discover_tool_modules()
    logger.info(f"Total modules to register: {len(modules)}")

    registrar = ToolRegistrar(mcp)
    for module_path in modules:
        logger.info(f"Registering tools from: {module_path}")
        module = importlib.import_module(module_path)
        if not hasattr(module, "register_tools"):
            raise ImportError(f"Tool module {module_path} has no register_tools(mcp, client) function")
        module.register_tools(registrar, client)


__all__ = ['ToolRegistrar', 'discover_tool_modules', 'register_all_tools']