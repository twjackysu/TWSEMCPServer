"""分層規則的守門測試（不打網路）。

tools/     各個 tool 模組，可以用下面所有層。
toolkit/   MCP 端的積木：錯誤邊界（handle_api_errors）、tool spec 與 factory。只依賴 utils。
services/  由多個 gateway 組成的資料服務（例如 price_series）。依賴 sources、utils。
sources/   gateway：每個上游端點一個模組，唯一知道該端點欄位長相的地方。只依賴 utils。
utils/     最底層：HTTP client、解析、格式化、日期。不認識 MCP。
prompts/   prompt 模板，純文字；自動註冊（register_all_prompts 收到 mcp 與工具 tags），不 import 本專案其他套件。

依賴只能往下：utils 曾經 import fastmcp（tool_factory、decorators），utils/__init__ 與 tool_factory
還互相 import。只有 tools/ 與 toolkit/ 可以碰 fastmcp。
"""

import ast
import pathlib
import subprocess
import sys

import pytest

pytestmark = pytest.mark.offline

ROOT = pathlib.Path(__file__).resolve().parents[2]


def _imported_top_modules(package: str):
    """(file, line, top-level module) for every absolute import in ``package``'s .py files."""
    for path in sorted((ROOT / package).rglob("*.py")):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                names = [node.module]
            else:
                continue
            for name in names:
                yield path.relative_to(ROOT), node.lineno, name.split(".")[0]


MCP = {"fastmcp", "mcp"}


@pytest.mark.parametrize("package, forbidden", [
    ("utils", MCP | {"toolkit", "tools", "services", "sources"}),
    ("sources", MCP | {"toolkit", "tools", "services"}),
    ("services", MCP | {"toolkit", "tools"}),
    ("toolkit", {"tools", "services", "sources"}),
    ("prompts", {"toolkit", "tools", "services", "sources", "utils"}),
])
def test_dependencies_only_point_down(package, forbidden):
    offenders = [f"{f}:{line} imports {mod}" for f, line, mod in _imported_top_modules(package) if mod in forbidden]
    assert offenders == [], "\n".join(offenders)


def _fresh_import(code: str) -> str:
    result = subprocess.run([sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


@pytest.mark.parametrize("module", ["utils", "sources.twse.stock_day", "services.price_series"])
def test_data_side_does_not_load_fastmcp(module):
    """在全新的 interpreter 裡只 import 資料端：連間接載入 fastmcp 都不行."""
    loaded = _fresh_import(f"import sys, {module}; print(sorted(m for m in sys.modules if m.split('.')[0] in ('fastmcp', 'mcp')))")
    assert loaded == "[]"


@pytest.mark.parametrize("module", ["utils", "sources", "services", "toolkit", "tools", "prompts"])
def test_each_package_imports_on_its_own(module):
    """各自在全新的 interpreter 裡 import：循環 import 只會在某些 import 順序下才出錯."""
    _fresh_import(f"import {module}")


def test_dockerfile_copies_every_package_the_server_imports():
    """Dockerfile 逐一 COPY 目錄：新增頂層套件（例如 toolkit/）卻忘了加，image 一啟動就 ImportError."""
    copied = {line.split()[1].strip("/").rstrip("/") for line in (ROOT / "Dockerfile").read_text(encoding="utf-8").splitlines()
              if line.startswith("COPY ")}
    packages = {p.parent.name for p in ROOT.glob("*/__init__.py")} - {"tests"}
    assert packages <= copied, f"Dockerfile 沒有 COPY：{sorted(packages - copied)}"
