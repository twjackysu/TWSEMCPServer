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
# A deployment can serve a subset (show_only_sources). The names, in this order, open the server
# instructions (server.py).
SOURCES = {
    "twse": "證交所",          # OpenAPI, website rwd / exchangeReport, MIS quotes
    "tpex": "櫃買中心",
    "taifex": "期交所",
    "mops": "公開資訊觀測站",
    "tdcc": "集保結算所",
    "sitca": "投信投顧公會",
    "ndc": "國發會",
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


def enabled_sources(include: str = "", exclude: str = "") -> FrozenSet[str]:
    """The sources a deployment serves: ``include`` (comma-separated tags; empty = every source) minus ``exclude``.

    An unknown name is an error rather than ignored, since a typo would hide tools without a word.
    """
    def names(text: str) -> set:
        found = {name.strip().lower() for name in text.split(",") if name.strip()}
        unknown = found - set(SOURCES)
        if unknown:
            raise ValueError(f"unknown data source(s) {sorted(unknown)}; known sources: {', '.join(SOURCES)}")
        return found

    served = frozenset((names(include) or set(SOURCES)) - names(exclude))
    if not served:
        raise ValueError("every data source is excluded: the server would have no tools")
    return served


def show_only_sources(mcp: "FastMCP", sources: FrozenSet[str]) -> None:
    """Hide what depends on sources outside ``sources``, with FastMCP's Visibility transform on tags.

    - A tool is hidden when any source it reads is off, since it could not answer in full
      (``get_etf_info`` reads sitca, twse and tpex). Calling a hidden tool fails as an unknown tool.
    - A prompt stays while any of its sources is on: a prompt walks through tools of several sources
      and is still useful with some of them. Its tags are the sources of the tools it names.
    - Untagged components are left alone.
    """
    hidden = set(SOURCES) - sources
    if not hidden:
        return
    mcp.disable(tags=hidden)
    mcp.enable(tags=set(sources), components={"prompt"})  # later Visibility marks win
    logger.info(f"Serving sources {sorted(sources)}; tools reading {sorted(hidden)} are hidden")


class ToolRegistrar:
    """The ``mcp`` every ``register_tools(mcp, client)`` receives: ``mcp.tool`` with server-wide defaults.

    Tool modules only call ``mcp.tool`` (bare, with keywords, or ``mcp.tool(name=...)(fn)``), and
    this forwards each call to FastMCP, adding defaults that should hold for every tool:

    - ``output_schema=None`` for a tool whose return type is ``str``. FastMCP 4 would otherwise
      give it a ``{"result": string}`` output schema and send the text twice per call, in
      ``content`` and again in ``structuredContent``.
    - ``annotations=READ_ONLY``: every tool only reads.
    - ``tags``: the data source(s) of the registering module (``SOURCE_TAGS``).

    A keyword the tool passes itself always wins. ``registered``, when given, collects each tool's
    name and final tags (``register_all_tools`` returns it, to tag the prompts).
    """

    def __init__(self, mcp: "FastMCP", tags: FrozenSet[str] = frozenset(),
                 registered: Optional[Dict[str, FrozenSet[str]]] = None):
        self._mcp = mcp
        self._tags = tags
        self._registered = registered

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
        if self._registered is not None:
            self._registered[kwargs.get("name") or fn.__name__] = frozenset(kwargs.get("tags") or ())
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


def register_all_tools(mcp: "FastMCP", client: Optional["TWSEAPIClient"] = None) -> Dict[str, FrozenSet[str]]:
    """
    Automatically discover and register all MCP tools from submodules.

    Fails fast: a module that cannot be imported, lacks ``register_tools`` or raises while
    registering stops the server from starting. Logging and carrying on would start a
    server that silently lacks that module's tools.

    Modules register through a ``ToolRegistrar`` around ``mcp``, which applies the server-wide
    tool defaults and the module's source tags. Returns every registered tool's tags by name
    (``prompts.register_all_prompts`` tags each prompt with those of the tools it names).

    Args:
        mcp: FastMCP instance to register tools with
        client: TWSEAPIClient instance for dependency injection
    """
    modules = discover_tool_modules()
    logger.info(f"Total modules to register: {len(modules)}")

    registered: Dict[str, FrozenSet[str]] = {}
    for module_path in modules:
        logger.info(f"Registering tools from: {module_path}")
        module = importlib.import_module(module_path)
        if not hasattr(module, "register_tools"):
            raise ImportError(f"Tool module {module_path} has no register_tools(mcp, client) function")
        module.register_tools(ToolRegistrar(mcp, tags=source_tags(module_path), registered=registered), client)
    return registered


__all__ = ['READ_ONLY', 'SOURCES', 'SOURCE_TAGS', 'ToolRegistrar', 'discover_tool_modules', 'enabled_sources',
           'register_all_tools', 'show_only_sources', 'source_tags']