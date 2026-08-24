"""
@file        kumihimo/compile/strategies/__init__.py
@purpose     The strategy registry: Section (the unit every strategy produces),
             the built-in registrations, and third-party loading via the
             kumihimo.strategies entry-point group.
@layer       compile
@tags        strategies, registry, entry-points, sections
@related     kumihimo/compile/strategies/linear.py (one sequence),
             kumihimo/compile/strategies/grouped.py (sections by membership),
             kumihimo/compile/weave.py (consumes the sections)
@design      PLAN.md §4.2
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from importlib import metadata
from typing import TYPE_CHECKING

from kumihimo.core.errors import KumihimoError

if TYPE_CHECKING:
    from kumihimo.core.plan import Plan


@dataclass
class Section:
    """One stretch of the woven output: an optional title and intro node, then
    ordered member ids.

    @purpose  The whole strategy contract — order between and within sections is
              the strategy's promise; rendering them is weave's job.
    """

    node_ids: list[str]
    title: str | None = None
    intro_id: str | None = None


Strategy = Callable[["Plan", list[str], list[str]], list[Section]]
"""A strategy maps (plan, ordered selected ids, warnings-sink) to sections."""

_REGISTRY: dict[str, Strategy] = {}
_ENTRY_POINTS_LOADED = False


def register(name: str, strategy: Strategy) -> None:
    """Add a strategy under a name.

    @purpose  Same door for built-ins and third parties.
    """
    _REGISTRY[name] = strategy


def _load_entry_points() -> None:
    """Pull in third-party strategies declared under kumihimo.strategies.

    @purpose  A plugin registers by packaging metadata alone — no imports of the
              plugin from our side, no config file.
    """
    global _ENTRY_POINTS_LOADED
    if _ENTRY_POINTS_LOADED:
        return
    _ENTRY_POINTS_LOADED = True
    for entry in metadata.entry_points(group="kumihimo.strategies"):
        register(entry.name, entry.load())


def get_strategy(name: str) -> Strategy:
    """Resolve a strategy by name or fail naming what exists.

    @purpose  The braid's one lookup; the error teaches the flag's vocabulary.
    """
    _load_entry_points()
    _ensure_builtins()
    strategy = _REGISTRY.get(name)
    if strategy is None:
        known = ", ".join(sorted(_REGISTRY))
        raise KumihimoError(f"unknown strategy '{name}' (available: {known})")
    return strategy


def _ensure_builtins() -> None:
    """Register the shipped strategies on first use.

    @purpose  Imported lazily so the registry module stays import-cycle-free.
    """
    if "linear" not in _REGISTRY:
        from kumihimo.compile.strategies.grouped import grouped
        from kumihimo.compile.strategies.linear import linear

        register("linear", linear)
        register("grouped", grouped)
