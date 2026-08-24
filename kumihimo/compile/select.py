"""
@file        kumihimo/compile/select.py
@purpose     Stage one of the braid: decide which nodes are in. Filters compose
             by intersection (--where on effective fields, --from/--until cones,
             --in membership), and the excluded direct dependencies of selected
             nodes are kept as stubs so the prompt never references a ghost.
@layer       compile
@tags        braid, selection, slicing, stubs
@related     kumihimo/compile/braid.py (the pipeline this feeds),
             kumihimo/core/graph.py (the cones)
@design      PLAN.md §4.1 step 1
"""

from __future__ import annotations

from dataclasses import dataclass, field

from kumihimo.core import graph, kinds
from kumihimo.core.errors import KumihimoError
from kumihimo.core.plan import Plan


@dataclass
class Selection:
    """The braid's working set: chosen ids plus the stub ids they lean on.

    @purpose  Selection is the only stage that knows why a node is absent; stubs
              carry that knowledge forward.
    """

    ids: list[str]
    stubs: list[str] = field(default_factory=list)


def _matches(plan: Plan, node_id: str, key: str, wanted: str) -> bool:
    """Whether a node's effective field equals (or, for lists, contains) a value.

    @purpose  `--where status=todo` and `--where acceptance=reviewed` both mean
              what they look like they mean.
    """
    node = plan.nodes[node_id]
    kind = plan.kinds.get(node.kind)
    effective = kinds.effective_fields(node, kind) if kind else dict(node.fields)
    if key == "kind":
        return node.kind == wanted
    value = effective.get(key)
    if value is None:
        return False
    if isinstance(value, list):
        return wanted in [str(item) for item in value]
    return str(value) == wanted


def select(
    plan: Plan,
    *,
    where: dict[str, str] | None = None,
    from_: str | None = None,
    until: str | None = None,
    in_: str | None = None,
) -> Selection:
    """Choose the braid's nodes; filters intersect, stubs bridge the cut edges.

    @purpose  One place where slicing semantics live, shared by braid, --dry,
              and (later) the MCP braid tool.
    @tags     selection, filters
    """
    chosen = set(plan.nodes)
    if from_ is not None:
        if from_ not in plan.nodes:
            raise KumihimoError(f"--from: no node '{from_}'")
        chosen &= {from_} | graph.descendants(plan.nodes, from_)
    if until is not None:
        if until not in plan.nodes:
            raise KumihimoError(f"--until: no node '{until}'")
        chosen &= {until} | graph.ancestors(plan.nodes, until)
    if in_ is not None:
        if in_ not in plan.nodes:
            raise KumihimoError(f"--in: no node '{in_}'")
        members = {node.id for node in plan.nodes.values() if in_ in node.in_}
        chosen &= members | {in_}
    for key, wanted in (where or {}).items():
        chosen = {node_id for node_id in chosen if _matches(plan, node_id, key, wanted)}
    if not chosen:
        raise KumihimoError("selection matches no nodes")
    stubs = {
        dep
        for node_id in chosen
        for dep in plan.nodes[node_id].needs
        if dep in plan.nodes and dep not in chosen
    }
    return Selection(ids=sorted(chosen), stubs=sorted(stubs))
