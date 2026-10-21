"""分層規則的守門測試（不打網路）。

utils/  資料端：HTTP client、解析、格式化。不認識 MCP，不 import fastmcp / toolkit / tools。
toolkit/ MCP 端的積木：錯誤邊界（handle_api_errors）、tool spec 與 factory。只往下依賴 utils。
tools/  各個 tool 模組，可以用以上兩者。

依賴只能往下：utils 曾經 import fastmcp（tool_factory、decorators），utils/__init__ 與 tool_factory
還互相 import。
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


@pytest.mark.parametrize("package, forbidden", [
    ("utils", {"fastmcp", "mcp", "toolkit", "tools"}),
    ("toolkit", {"tools"}),
])
def test_dependencies_only_point_down(package, forbidden):
    offenders = [f"{f}:{line} imports {mod}" for f, line, mod in _imported_top_modules(package) if mod in forbidden]
    assert offenders == [], "\n".join(offenders)


def _fresh_import(code: str) -> str:
    result = subprocess.run([sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


def test_importing_utils_does_not_load_fastmcp():
    """在全新的 interpreter 裡只 import utils：連間接載入 fastmcp 都不行."""
    loaded = _fresh_import("import sys, utils; print(sorted(m for m in sys.modules if m.split('.')[0] in ('fastmcp', 'mcp')))")
    assert loaded == "[]"


@pytest.mark.parametrize("module", ["utils", "toolkit", "tools"])
def test_each_package_imports_on_its_own(module):
    """各自在全新的 interpreter 裡 import：循環 import 只會在某些 import 順序下才出錯."""
    _fresh_import(f"import {module}")


def test_dockerfile_copies_every_package_the_server_imports():
    """Dockerfile 逐一 COPY 目錄：新增頂層套件（例如 toolkit/）卻忘了加，image 一啟動就 ImportError."""
    copied = {line.split()[1].strip("/").rstrip("/") for line in (ROOT / "Dockerfile").read_text(encoding="utf-8").splitlines()
              if line.startswith("COPY ")}
    packages = {p.parent.name for p in ROOT.glob("*/__init__.py")} - {"tests"}
    assert packages <= copied, f"Dockerfile 沒有 COPY：{sorted(packages - copied)}"
