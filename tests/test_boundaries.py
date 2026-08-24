"""
@file        tests/test_boundaries.py
@purpose     Enforces PLAN.md §7.1 invariant 3: core/ and compile/ import no
             client-layer or UI/server/template library code. The boundary is a
             test, not a good intention (Whetstone's test_core_has_no_gui_imports
             is the precedent).
@layer       tests
@tags        boundaries, imports, architecture
@related     kumihimo/core/__init__.py (the protected layer),
             kumihimo/compile/__init__.py (protected, may import core)
@design      PLAN.md §7.1
"""

import ast
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

FORBIDDEN: dict[str, set[str]] = {
    "kumihimo/core": {
        "typer",
        "click",
        "rich",
        "fastapi",
        "starlette",
        "uvicorn",
        "mcp",
        "jinja2",
        "watchfiles",
        "kumihimo.cli",
        "kumihimo.server",
        "kumihimo.mcp",
        "kumihimo.compile",
    },
    "kumihimo/compile": {
        "typer",
        "click",
        "rich",
        "fastapi",
        "starlette",
        "uvicorn",
        "mcp",
        "watchfiles",
        "kumihimo.cli",
        "kumihimo.server",
        "kumihimo.mcp",
    },
}


def resolved_imports(py_file: Path) -> list[str]:
    """Absolute module names a file imports, with relative imports resolved.

    @purpose  Boundary checks must see `from .. import mcp` as kumihimo.mcp, or the
              rule is trivially dodged with a relative import.
    """
    tree = ast.parse(py_file.read_text(encoding="utf-8"))
    package_parts = py_file.relative_to(REPO).with_suffix("").parts
    if package_parts[-1] == "__init__":
        package_parts = package_parts[:-1]
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0:
                base = node.module or ""
            else:
                anchor = package_parts[: len(package_parts) - node.level]
                base = ".".join((*anchor, node.module) if node.module else anchor)
            found.append(base)
            found.extend(f"{base}.{alias.name}" for alias in node.names if base)
    return found


def test_core_and_compile_import_no_client_code() -> None:
    for folder, banned in FORBIDDEN.items():
        for py_file in sorted((REPO / folder).rglob("*.py")):
            for module in resolved_imports(py_file):
                for bad in banned:
                    hit = module == bad or module.startswith(bad + ".")
                    assert not hit, f"{py_file.relative_to(REPO)} imports {module}"
