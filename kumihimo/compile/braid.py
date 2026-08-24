"""
@file        kumihimo/compile/braid.py
@purpose     The pipeline itself: gate on check errors, select, order, hand to
             the strategy, weave — or stop at --dry with just the order. Returns
             a BraidResult carrying text, order, sections, and warnings.
@layer       compile
@tags        braid, pipeline, dry-run
@related     kumihimo/compile/select.py, kumihimo/compile/strategies/__init__.py,
             kumihimo/compile/weave.py (the stages, in order),
             kumihimo/core/plan.py (Plan.braid sugars this)
@design      PLAN.md §4.1
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from kumihimo.compile.select import Selection, select
from kumihimo.compile.strategies import Section, get_strategy
from kumihimo.compile.weave import assign_numbers, weave
from kumihimo.core import graph
from kumihimo.core.errors import KumihimoError

if TYPE_CHECKING:
    from kumihimo.core.plan import Plan


@dataclass
class BraidResult:
    """Everything one braid produced.

    @purpose  Clients that want more than the text (the editor's preview, tests,
              --dry) get the structure without re-deriving it.
    """

    text: str
    order: list[str]
    sections: list[Section]
    selection: Selection
    warnings: list[str] = field(default_factory=list)


def _gate_on_errors(plan: Plan) -> None:
    """Refuse to braid a plan whose check has errors.

    @purpose  A deterministic artifact from invalid input is a lie; the gate
              names the first few problems and points at check.
    """
    errors = [finding for finding in plan.check() if finding.level == "error"]
    if errors:
        shown = "; ".join(finding.render() for finding in errors[:3])
        more = f" (+{len(errors) - 3} more)" if len(errors) > 3 else ""
        raise KumihimoError(
            f"plan has {len(errors)} check error(s) — fix before braiding: {shown}{more}"
        )


def _dry_text(plan: Plan, sections: list[Section], strategy_name: str) -> str:
    """The order without the rendering, like make -n.

    @purpose  See what a braid would do — order, sections, numbering — in a
              screenful, before generating pages.
    """
    numbers = assign_numbers(sections)
    lines = [f"braid order ({strategy_name}):"]
    for section in sections:
        if section.title:
            lines.append(f"  [{section.title}]")
        for node_id in section.node_ids:
            node = plan.nodes[node_id]
            lines.append(f"  {numbers[node_id]:3d}. {node_id} — {node.title} ({node.kind})")
    return "\n".join(lines) + "\n"


def braid(
    plan: Plan,
    *,
    strategy: str | None = None,
    where: dict[str, str] | None = None,
    from_: str | None = None,
    until: str | None = None,
    in_: str | None = None,
    diagram: bool | None = None,
    dry: bool = False,
) -> BraidResult:
    """Compile a plan (or a slice of it) into one deterministic prompt.

    @purpose  The whole point of the tool, as one function: same plan and
              arguments in, byte-identical text out.
    @tags     braid, pipeline
    """
    _gate_on_errors(plan)
    selection = select(plan, where=where, from_=from_, until=until, in_=in_)
    sub_nodes = {node_id: plan.nodes[node_id] for node_id in selection.ids}
    ordered = graph.braid_order(sub_nodes)
    strategy_name = strategy or plan.manifest.compile.strategy
    strategy_fn = get_strategy(strategy_name)
    warnings: list[str] = []
    sections = strategy_fn(plan, ordered, warnings)
    if dry:
        text = _dry_text(plan, sections, strategy_name)
    else:
        show_diagram = plan.manifest.compile.diagram if diagram is None else diagram
        text = weave(plan, sections, selection, diagram=show_diagram, warnings=warnings)
    numbered = assign_numbers(sections)
    order = sorted(numbered, key=lambda node_id: numbered[node_id])
    return BraidResult(
        text=text, order=order, sections=sections, selection=selection, warnings=warnings
    )
