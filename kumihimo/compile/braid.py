"""
@file        kumihimo/compile/braid.py
@purpose     The pipeline itself: gate on check errors, select, order, carve
             out crew nodes for grouped's Cast section, hand the rest to the
             strategy, weave — or stop at --dry with just the order. Returns
             a BraidResult carrying text, order, sections, and warnings.
@layer       compile
@tags        braid, pipeline, dry-run, cast, for-agent
@related     kumihimo/compile/select.py, kumihimo/compile/strategies/__init__.py,
             kumihimo/compile/weave.py (the stages, in order),
             kumihimo/core/plan.py (Plan.braid sugars this)
@design      PLAN.md §4.1, PLAN2.md §3.3
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from kumihimo.compile.select import Selection, select
from kumihimo.compile.strategies import Section, get_strategy
from kumihimo.compile.weave import assign_numbers, weave
from kumihimo.core import graph
from kumihimo.core import kinds as kinds_module
from kumihimo.core.errors import KumihimoError

if TYPE_CHECKING:
    from kumihimo.core.plan import Plan

# Kinds Cast carves out of grouped's numbered flow (PLAN2 §3.1) — reference
# nodes stay in the ordinary flow since nothing selects them by mention alone.
_CREW_KINDS = ("agent", "skill")


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


def gate_on_errors(plan: Plan) -> None:
    """Refuse to produce a machine-feed artifact from a plan whose check has
    errors.

    @purpose  A deterministic artifact from invalid input is a lie; the gate
              names the first few problems and points at check. Shared by
              braid() below and export.jsonl() (kumihimo/compile/export.py)
              — both are machine feeds a downstream tool trusts. mermaid/dot
              export stays ungated on purpose: those are diagnostic pictures,
              and seeing a broken plan drawn is exactly when they earn their
              keep (docs/reference/cli.md documents the split).
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


def _ground_with(plan: Plan, for_agent: str) -> str | None:
    """The `--for` agent's standing grounding command, or None when it has none.

    @purpose  PLAN2 §3.7's Lantern pattern: an agent's `retrieval` field opens
              its work orders as *Ground with:*, silently omitted when absent —
              never a clock, never a fetch, just a string carried verbatim.
    """
    agent = plan.nodes[for_agent]
    kind = plan.kinds.get(agent.kind)
    effective = kinds_module.effective_fields(agent, kind) if kind else dict(agent.fields)
    retrieval = effective.get("retrieval")
    return str(retrieval) if retrieval else None


def _cast_ids(plan: Plan, ordered: list[str], for_agent: str | None) -> list[str]:
    """Every crew member the grouped braid's text actually cites, sorted
    (kind, id).

    @purpose  Cast must introduce everyone the rendered items name — a crew
              member `--where` (or any other filter) drops from the
              selection is still cited by every *Assigned:*/*With:*/
              *Trains:* line, because render.py's mention lines read
              plan.nodes directly and don't care whether their target was
              selected. So the cast set is three unions: crew nodes that
              *are* selected, crew nodes any selected node's agents:/
              skills:/trains: names (selected or not), and --for's own
              agent (it grounds the braid even when a composed --where
              filters it out of the numbered work, since an agent kind
              carries no `status` field for --where to match).
    @tags     cast, mentions, for-agent
    """
    selected_crew = {node_id for node_id in ordered if plan.nodes[node_id].kind in _CREW_KINDS}
    cited_crew = {
        target
        for node_id in ordered
        for target in (
            *plan.nodes[node_id].agents,
            *plan.nodes[node_id].skills,
            *plan.nodes[node_id].trains,
        )
        if target in plan.nodes and plan.nodes[target].kind in _CREW_KINDS
    }
    cast_set = selected_crew | cited_crew
    if for_agent is not None:
        cast_set.add(for_agent)
    return sorted(cast_set, key=lambda node_id: (plan.nodes[node_id].kind, node_id))


def braid(
    plan: Plan,
    *,
    strategy: str | None = None,
    where: dict[str, str] | None = None,
    from_: str | None = None,
    until: str | None = None,
    in_: str | None = None,
    for_agent: str | None = None,
    diagram: bool | None = None,
    dry: bool = False,
) -> BraidResult:
    """Compile a plan (or a slice of it) into one deterministic prompt.

    @purpose  The whole point of the tool, as one function: same plan and
              arguments in, byte-identical text out. `for_agent` (--for)
              compiles one agent's work orders: nodes that mention it, the
              skills those tasks in turn mention, and the agent itself —
              anything else the agent's own edges point at degrades through
              the ordinary stub machinery, like any out-of-selection
              dependency. Opens with *Ground with:* when the agent carries a
              `retrieval` field.
    @tags     braid, pipeline, for-agent
    """
    gate_on_errors(plan)
    selection = select(plan, where=where, from_=from_, until=until, in_=in_, for_agent=for_agent)
    sub_nodes = {node_id: plan.nodes[node_id] for node_id in selection.ids}
    ordered = graph.braid_order(sub_nodes)
    strategy_name = strategy or plan.manifest.compile.strategy
    strategy_fn = get_strategy(strategy_name)
    warnings: list[str] = []
    # Grouped's Cast section briefs the crew separately from the numbered
    # work (PLAN2 §3.3); every other strategy renders agent/skill nodes
    # exactly like anything else, so only grouped carves them out here. Only
    # a cast member that is itself IN the selection gets excluded from the
    # numbered flow — one merely cited (or forced in by --for) was never
    # going to be numbered in the first place, so there's nothing to remove.
    cast_ids: list[str] = []
    strategy_input = ordered
    if strategy_name == "grouped":
        cast_ids = _cast_ids(plan, ordered, for_agent)
        excluded = set(cast_ids) & set(ordered)
        if excluded:
            strategy_input = [node_id for node_id in ordered if node_id not in excluded]
    sections = strategy_fn(plan, strategy_input, warnings)
    ground_with = _ground_with(plan, for_agent) if for_agent is not None else None
    if dry:
        text = _dry_text(plan, sections, strategy_name)
    else:
        show_diagram = plan.manifest.compile.diagram if diagram is None else diagram
        text = weave(
            plan,
            sections,
            selection,
            diagram=show_diagram,
            warnings=warnings,
            cast_ids=cast_ids,
            ground_with=ground_with,
        )
    numbered = assign_numbers(sections)
    order = sorted(numbered, key=lambda node_id: numbered[node_id])
    return BraidResult(
        text=text, order=order, sections=sections, selection=selection, warnings=warnings
    )
