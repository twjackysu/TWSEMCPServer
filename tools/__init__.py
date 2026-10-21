"""MCP tools for TWStockMCPServer."""

import importlib
import inspect
import pkgutil
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Dict, FrozenSet, List, Optional

from mcp.types import ToolAnnotations

if TYPE_CHECKING:
    from fastmcp import FastMCP
    from utils.api_client import TWSEAPIClient

logger = logging.getLogger(__name__)

# Every tool only reads public market data from a third-party site: it changes nothing, the same call
# can be repeated freely, and it reaches outside the server. Clients may use these hints to call tools
# without asking for confirmation, or in parallel.
# (MCP SDK v2 field names; on the wire they are readOnlyHint, destructiveHint, idempotentHint, openWorldHint.)
READ_ONLY = ToolAnnotations(read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=True)

# The data provider(s) behind each tool module, as tags. The longest matching module prefix applies.
# A deployment can serve a subset with FastMCP's Visibility transform (e.g. only twse and tpex).
SOURCES = {
    "twse": "臺灣證券交易所（OpenAPI、網站 rwd／exchangeReport、MIS 即時行情）",
    "tpex": "證券櫃檯買賣中心",
    "taifex": "臺灣期貨交易所",
    "mops": "公開資訊觀測站",
    "tdcc": "臺灣集中保管結算所",
    "sitca": "中華民國證券投資信託暨顧問商業同業公會",
    "ndc": "國家發展委員會",
    "cbc": "中央銀行",
}
SOURCE_TAGS: Dict[str, FrozenSet[str]] = {
    "tools.analytics": frozenset({"twse", "tpex"}),       # price series and snapshots of both markets
    "tools.broker": frozenset({"twse"}),
    "tools.company": frozenset({"twse"}),
    "tools.etf.daily_nav": frozenset({"twse"}),          # MIS all_etf.txt (listed and OTC ETFs)
    "tools.etf.holdings": frozenset({"sitca"}),
    "tools.etf.info": frozenset({"sitca", "twse", "tpex"}),
    "tools.etf.monthly_stats": frozenset({"sitca"}),
    "tools.history": frozenset({"twse"}),
    "tools.macro.exchange_rates": frozenset({"cbc"}),
    "tools.macro.ndc_indicators": frozenset({"ndc"}),
    "tools.market": frozenset({"twse"}),
    "tools.mops": frozenset({"mops"}),
    "tools.otc": frozenset({"tpex"}),
    "tools.other": frozenset({"twse"}),
    "tools.realtime": frozenset({"twse"}),               # MIS quotes, listed and OTC
    "tools.taifex": frozenset({"taifex"}),
    "tools.tdcc": frozenset({"tdcc"}),
    "tools.trading": frozenset({"twse"}),
}


def source_tags(module_path: str) -> FrozenSet[str]:
    """The source tags of a tool module (its longest prefix in ``SOURCE_TAGS``); a module without one is an error."""
    prefixes = [p for p in SOURCE_TAGS if module_path == p or module_path.startswith(p + ".")]
    if not prefixes:
        raise LookupError(f"{module_path} has no entry in tools.SOURCE_TAGS: say which source(s) its tools read")
    return SOURCE_TAGS[max(prefixes, key=len)]


class ToolRegistrar:
    """The ``mcp`` every ``register_tools(mcp, client)`` receives: ``mcp.tool`` with server-wide defaults.

    Tool modules only call ``mcp.tool`` (bare, with keywords, or ``mcp.tool(name=...)(fn)``), and
    this forwards each call to FastMCP, adding defaults that should hold for every tool:

    - ``output_schema=None`` for a tool whose return type is ``str``. FastMCP 4 would otherwise
      give it a ``{"result": string}`` output schema and send the text twice per call, in
      ``content`` and again in ``structuredContent``.
    - ``annotations=READ_ONLY``: every tool only reads.
    - ``tags``: the data source(s) of the registering module (``SOURCE_TAGS``).

    A keyword the tool passes itself always wins.
    """

    def __init__(self, mcp: "FastMCP", tags: FrozenSet[str] = frozenset()):
        self._mcp = mcp
        self._tags = tags

    def tool(self, name_or_fn: Any = None, **kwargs: Any) -> Any:
        if callable(name_or_fn):
            return self._register(name_or_fn, None, kwargs)
        return lambda fn: self._register(fn, name_or_fn, kwargs)

    def _register(self, fn: Callable[..., Any], name: Optional[str], kwargs: dict) -> Any:
        if inspect.signature(fn, eval_str=True).return_annotation is str:
            kwargs = {"output_schema": None, **kwargs}
        kwargs = {"annotations": READ_ONLY, **kwargs}
        if self._tags:
            kwargs = {"tags": set(self._tags), **kwargs}
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
    tool defaults and the module's source tags.

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
        module.register_tools(ToolRegistrar(mcp, tags=source_tags(module_path)), client)


__all__ = ['READ_ONLY', 'SOURCES', 'SOURCE_TAGS', 'ToolRegistrar', 'discover_tool_modules', 'register_all_tools',
           'source_tags']