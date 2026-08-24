"""
@file        kumihimo/__init__.py
@purpose     Public entry point of the kumihimo package: the version constant and
             the re-exported public API (Plan, Node, Finding, KumihimoError).
@layer       package-root
@tags        public-api, version
@related     kumihimo/core/plan.py (Plan lives there),
             kumihimo/cli/app.py (the CLI over this API)
@design      PLAN.md §7.2
"""

from kumihimo.compile import BraidResult, braid
from kumihimo.compile import export as export
from kumihimo.core.errors import CycleError, KumihimoError
from kumihimo.core.model import Finding, Node
from kumihimo.core.plan import Plan

__version__ = "0.1.0.dev0"

__all__ = [
    "BraidResult",
    "CycleError",
    "Finding",
    "KumihimoError",
    "Node",
    "Plan",
    "__version__",
    "braid",
    "export",
]
