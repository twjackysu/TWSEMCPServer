"""MCP prompt templates for stock analysis.

Every module here holds one prompt: a public function whose name is the prompt's name, whose
docstring is its description and whose parameters are its arguments. ``register_all_prompts`` finds
them all, so a new prompt needs only its module. Templates are plain text: this package imports
nothing else from the server.
"""

import importlib
import inspect
import logging
import pkgutil
import re
from pathlib import Path
from types import ModuleType
from typing import TYPE_CHECKING, Callable, FrozenSet, List, Mapping

if TYPE_CHECKING:
    from fastmcp import FastMCP

logger = logging.getLogger(__name__)

# A tool a prompt tells the model to call: get_xxx(...) inside backticks.
TOOL_REFERENCE = re.compile(r"`(get_[a-z0-9_]+)\(")


def discover_prompt_modules() -> List[str]:
    """Dotted names of every prompt module (``prompts/*.py``), sorted."""
    return sorted(f"prompts.{info.name}" for info in pkgutil.iter_modules([str(Path(__file__).parent)])
                  if not info.ispkg)


def prompt_of(module: ModuleType) -> Callable[..., str]:
    """The module's prompt: the one public function it defines."""
    functions = [fn for name, fn in inspect.getmembers(module, inspect.isfunction)
                 if fn.__module__ == module.__name__ and not name.startswith("_")]
    if len(functions) != 1:
        raise ImportError(f"Prompt module {module.__name__} must define exactly one public function (the prompt), "
                          f"found {[fn.__name__ for fn in functions]}")
    return functions[0]


def prompt_tags(text: str, tool_tags: Mapping[str, FrozenSet[str]]) -> FrozenSet[str]:
    """The sources of the tools a prompt's text names (``tool_tags``: every registered tool's tags).

    Naming a tool that is not registered is an error: the prompt would send the model to a tool
    that does not exist.
    """
    named = sorted(set(TOOL_REFERENCE.findall(text)))
    unknown = [name for name in named if name not in tool_tags]
    if unknown:
        raise LookupError(f"prompt names tools that are not registered: {unknown}")
    return frozenset().union(*(tool_tags[name] for name in named))


def register_all_prompts(mcp: "FastMCP", tool_tags: Mapping[str, FrozenSet[str]]) -> None:
    """Register every prompt module's prompt, tagged with the sources of the tools it names.

    Register the tools first and pass what ``tools.register_all_tools`` returns. The tags let a
    deployment that serves only some sources hide a prompt none of whose tools it serves
    (``tools.show_only_sources``). Fails fast like the tools: a broken module stops the server.
    """
    for module_path in discover_prompt_modules():
        module = importlib.import_module(module_path)
        try:
            tags = prompt_tags(inspect.getsource(module), tool_tags)
        except LookupError as e:
            raise LookupError(f"{module_path}: {e}") from None
        logger.info(f"Registering prompt from: {module_path} (tags {sorted(tags)})")
        mcp.prompt(prompt_of(module), tags=set(tags))


__all__ = ['TOOL_REFERENCE', 'discover_prompt_modules', 'prompt_of', 'prompt_tags', 'register_all_prompts']
