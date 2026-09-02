"""
@file        kumihimo/compile/select.py
@purpose     Stage one of the braid: decide which nodes are in. Filters compose
             by intersection (--where on effective fields, --from/--until cones,
             --in membership, --for one agent's mentions), and the excluded
             direct dependencies of selected nodes are kept as stubs so the
             prompt never references a ghost.
@layer       compile
@tags        braid, selection, slicing, stubs, for-agent
@related     kumihimo/compile/braid.py (the pipeline this feeds),
             kumihimo/core/graph.py (the cones)
@design      PLAN.md §4.1 step 1, PLAN2.md §3.3
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


def validate_for_agent(plan: Plan, agent_id: str) -> None:
    """Raise the standard `--for` error if agent_id isn't a real `agent` node.

    @purpose  Shared by this module's own --for selection and the `ready`
              query's for_agent filter (kumihimo/mcp/tools.py, PLAN2 §3.3) so
              a missing or wrong-kind id is named identically from either
              door — one validator, not two copies that can drift.
    @tags     selection, for-agent, validation
    """
    if agent_id not in plan.nodes:
        raise KumihimoError(f"--for: no node '{agent_id}'")
    kind = plan.nodes[agent_id].kind
    if kind != "agent":
        raise KumihimoError(f"--for: '{agent_id}' is kind '{kind}', expected agent")


def _for_agent_base(plan: Plan, agent_id: str) -> set[str]:
    """The starting set for `--for agent_id`: everyone who works with them.

    @purpose  PLAN2 §3.3's "one agent's braid," read literally: every node
              mentioning the agent (agents:/skills:/trains: — checked
              generically, since a wrong-kind mention is a check error that
              already gated braid before selection runs), the agent itself,
              and the skill nodes the mentioning tasks in turn mention.
              Deliberately NOT the agent's own needs/in/links/mentions —
              those degrade through the ordinary stub machinery below (a
              `needs` target becomes a stub) or drop silently (anything
              else), exactly like an out-of-selection dependency for any
              other slice. Pulling them in whole rendered one unexplained
              full item in the braid with no citation pointing at it — the
              class of bug this restriction removes.
    @tags     selection, for-agent
    """
    validate_for_agent(plan, agent_id)
    mentioning = {
        node.id
        for node in plan.nodes.values()
        if agent_id in node.agents or agent_id in node.skills or agent_id in node.trains
    }
    mentioned_skills = {
        skill
        for node_id in mentioning
        for skill in plan.nodes[node_id].skills
        if skill in plan.nodes
    }
    return {agent_id} | mentioning | mentioned_skills


def select(
    plan: Plan,
    *,
    where: dict[str, str] | None = None,
    from_: str | None = None,
    until: str | None = None,
    in_: str | None = None,
    for_agent: str | None = None,
) -> Selection:
    """Choose the braid's nodes; filters intersect, stubs bridge the cut edges.

    @purpose  One place where slicing semantics live, shared by braid, --dry,
              and the MCP braid tool. `for_agent` replaces the "everything"
              starting point with one agent's working set; --where/--from/
              --until/--in still narrow it further, same as ever.
    @tags     selection, filters, for-agent
    """
    chosen = _for_agent_base(plan, for_agent) if for_agent is not None else set(plan.nodes)
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
