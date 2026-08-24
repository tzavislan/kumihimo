"""
@file        kumihimo/compile/export.py
@purpose     The public export surface: a plan as Mermaid or DOT text, exactly
             what `kumihimo export` and kumihimo.export.* hand out.
@layer       compile
@tags        export, mermaid, dot
@related     kumihimo/compile/diagram.py (generates what this exposes)
@design      PLAN.md §7.2
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from kumihimo.compile import diagram

if TYPE_CHECKING:
    from kumihimo.core.plan import Plan


def mermaid(plan: Plan) -> str:
    """The whole plan as a Mermaid graph.

    @purpose  Paste into any README; GitHub renders it natively.
    """
    return diagram.mermaid(plan)


def dot(plan: Plan) -> str:
    """The whole plan as Graphviz DOT.

    @purpose  For real layout engines and SVG/PDF pipelines.
    """
    return diagram.dot(plan)
