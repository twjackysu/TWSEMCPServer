"""MCP tools for TWStockMCPServer."""

import importlib
import pkgutil
import logging
from pathlib import Path
from typing import TYPE_CHECKING, List, Optional

if TYPE_CHECKING:
    from fastmcp import FastMCP
    from utils.api_client import TWSEAPIClient

logger = logging.getLogger(__name__)

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

    Args:
        mcp: FastMCP instance to register tools with
        client: TWSEAPIClient instance for dependency injection
    """
    modules = discover_tool_modules()
    logger.info(f"Total modules to register: {len(modules)}")

    for module_path in modules:
        logger.info(f"Registering tools from: {module_path}")
        module = importlib.import_module(module_path)
        if not hasattr(module, "register_tools"):
            raise ImportError(f"Tool module {module_path} has no register_tools(mcp, client) function")
        module.register_tools(mcp, client)


__all__ = ['discover_tool_modules', 'register_all_tools']