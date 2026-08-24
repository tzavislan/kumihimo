"""
@file        kumihimo/compile/strategies/linear.py
@purpose     The simplest braid: every selected node in one numbered sequence,
             already in deterministic topological order.
@layer       compile
@tags        strategies, linear
@related     kumihimo/compile/strategies/__init__.py (registry and contract)
@design      PLAN.md §4.2
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from kumihimo.compile.strategies import Section

if TYPE_CHECKING:
    from kumihimo.core.plan import Plan


def linear(plan: Plan, ordered: list[str], warnings: list[str]) -> list[Section]:
    """One untitled section holding the whole order.

    @purpose  The baseline every other strategy is judged against.
    """
    return [Section(node_ids=list(ordered))]
