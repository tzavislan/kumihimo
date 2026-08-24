"""
@file        kumihimo/compile/__init__.py
@purpose     The braid: select → order → render → weave. Exports braid and
             BraidResult, and registers itself as Plan.braid's implementation so
             core never has to import this package.
@layer       compile
@tags        braid, strategies, templates, public-api
@related     kumihimo/compile/braid.py (the pipeline),
             kumihimo/core/plan.py (the hook this registers into)
@design      PLAN.md §4
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from kumihimo.compile.braid import BraidResult, braid
from kumihimo.core import plan as _plan_module

if TYPE_CHECKING:
    from kumihimo.core.plan import Plan


def _braid_text(plan: Plan, **kwargs: Any) -> str:
    """Adapter: Plan.braid returns the text; the full BraidResult stays here.

    @purpose  Keeps the public sugar thin without narrowing the library API.
    """
    return braid(plan, **kwargs).text


_plan_module.register_braider(_braid_text)

__all__ = ["BraidResult", "braid"]
