"""MCP tools for TWStockMCPServer."""

import importlib
import pkgutil
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastmcp import FastMCP


def register_all_tools(mcp: "FastMCP") -> None:
    """
    Automatically discover and register all MCP tools from submodules.
    
    This function scans all Python modules in the tools package and its subpackages,
    looking for modules that have a register_tools function. It then calls each
    register_tools function to register the tools with the MCP instance.
    
    Args:
        mcp: FastMCP instance to register tools with
    """
    tools_package = Path(__file__).parent
    
    # Get all subpackages and modules
    modules_to_register = []
    
    # Scan direct modules in tools/
    for module_info in pkgutil.iter_modules([str(tools_package)]):
        if not module_info.ispkg and module_info.name != '__init__':
            modules_to_register.append(f"tools.{module_info.name}")
    
    # Scan subpackages (company, trading, market)
    for subpackage_info in pkgutil.iter_modules([str(tools_package)]):
        if subpackage_info.ispkg:
            subpackage_path = tools_package / subpackage_info.name
            for module_info in pkgutil.iter_modules([str(subpackage_path)]):
                if not module_info.ispkg and module_info.name != '__init__':
                    modules_to_register.append(f"tools.{subpackage_info.name}.{module_info.name}")
    
    # Import and register tools from each module
    for module_path in sorted(modules_to_register):
        try:
            module = importlib.import_module(module_path)
            if hasattr(module, 'register_tools'):
                module.register_tools(mcp)
        except Exception as e:
            # Log warning but continue with other modules
            import logging
            logging.warning(f"Failed to register tools from {module_path}: {e}")


__all__ = ['register_all_tools']