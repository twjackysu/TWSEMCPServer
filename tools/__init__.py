"""MCP tools for TWStockMCPServer."""

import importlib
import pkgutil
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from fastmcp import FastMCP
    from utils.api_client import TWSEAPIClient

logger = logging.getLogger(__name__)

def register_all_tools(mcp: "FastMCP", client: Optional["TWSEAPIClient"] = None) -> None:
    """
    Automatically discover and register all MCP tools from submodules.
    
    Args:
        mcp: FastMCP instance to register tools with
        client: TWSEAPIClient instance for dependency injection
    """
    try:
        tools_package = Path(__file__).parent.resolve()  # Use absolute path
        logger.info(f"Scanning tools in: {tools_package}")
        
        # Get all subpackages and modules
        modules_to_register = []
        
        # Scan direct modules in tools/
        for module_info in pkgutil.iter_modules([str(tools_package)]):
            if not module_info.ispkg and module_info.name != '__init__':
                full_name = f"tools.{module_info.name}"
                modules_to_register.append(full_name)
                logger.debug(f"Found module: {full_name}")
        
        # Scan subpackages (company, trading, market)
        for subpackage_info in pkgutil.iter_modules([str(tools_package)]):
            if subpackage_info.ispkg:
                subpackage_path = tools_package / subpackage_info.name
                for module_info in pkgutil.iter_modules([str(subpackage_path)]):
                    if not module_info.ispkg and module_info.name != '__init__':
                        full_name = f"tools.{subpackage_info.name}.{module_info.name}"
                        modules_to_register.append(full_name)
                        logger.debug(f"Found submodule: {full_name}")
        
        logger.info(f"Total modules to register: {len(modules_to_register)}")

        # Import and register tools from each module
        for module_path in sorted(modules_to_register):
            try:
                logger.info(f"Registering tools from: {module_path}")
                module = importlib.import_module(module_path)
                if hasattr(module, 'register_tools'):
                    # Simply call with client dependency
                    # All tool modules must now accept this signature
                    module.register_tools(mcp, client)
                    logger.info(f"Successfully registered tools from {module_path}")
                else:
                    logger.warning(f"Module {module_path} has no register_tools function")
                        
            except Exception as e:
                # Log warning but continue with other modules
                logger.error(f"Failed to register tools from {module_path}: {e}", exc_info=True)
                
    except Exception as e:
        logger.error(f"Critical error during tool discovery: {e}", exc_info=True)


__all__ = ['register_all_tools']