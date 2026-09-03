"""
@file        kumihimo/mcp/tools.py
@purpose     The MCP tools' actual behavior, as plain functions over a plan
             root — thin twins of the ops layer plus the read/braid/ready/
             crew queries, returning JSON-shaped dicts. server.py wraps these
             for transport; tests hit them directly, which is what keeps the
             CLI/MCP twins honest.
@layer       mcp
@tags        mcp, tools, ops-twins, ready, crew, for-agent
@related     kumihimo/core/ops.py (the mutations these front),
             kumihimo/core/crew.py (the roster computation crew() renders),
             kumihimo/mcp/server.py (the FastMCP registration)
@design      PLAN.md §6.1, PLAN2.md §3.3, §3.6
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from kumihimo.compile import braid as braid_pipeline
from kumihimo.compile.select import validate_for_agent
from kumihimo.core import crew as crew_module
from kumihimo.core import kinds as kinds_module
from kumihimo.core import ops
from kumihimo.core.model import Node
from kumihimo.core.plan import Plan

# A dependency is satisfied when it carries no status field at all, or its
# effective status is one of these terminal values (task/decision/question).
DONE_VALUES = frozenset({"done", "settled", "answered"})


def _summary(node: Node) -> dict[str, Any]:
    """The shape every read and mutating tool returns.

    @purpose  Enough to confirm what happened without re-fetching: identity,
              edges, mentions, and fields as written. agents/skills/trains
              (K36) mirror needs/in/links exactly: always present as a list,
              empty rather than omitted when the node mentions nothing —
              the same shape kumihimo/server/payload.py already gives the
              HTTP editor, so an MCP reader and the canvas never disagree on
              what a node carries.
    """
    return {
        "id": node.id,
        "kind": node.kind,
        "title": node.title,
        "needs": list(node.needs),
        "in": list(node.in_),
        "links": [{"to": link.to, "rel": link.rel} for link in node.links],
        "agents": list(node.agents),
        "skills": list(node.skills),
        "trains": list(node.trains),
        "priority": node.priority,
        "fields": dict(node.fields),
    }


def get_plan(root: Path) -> dict[str, Any]:
    """The whole graph, bodies elided.

    @purpose  One call to orient: manifest meta plus every node's identity and
              edges — get_node fetches the prose.
    """
    plan = Plan.load(root)
    return {
        "plan": plan.manifest.plan,
        "description": plan.manifest.description,
        "strategy": plan.manifest.compile.strategy,
        "kinds": sorted(plan.kinds),
        "nodes": [_summary(node) for _, node in sorted(plan.nodes.items())],
    }


def get_node(root: Path, node_id: str) -> dict[str, Any]:
    """One node in full: summary plus body and effective fields.

    @purpose  The read that pairs with update_node — effective fields show what
              templates and filters will actually see.
    """
    plan = Plan.load(root)
    node = plan.node(node_id)
    kind = plan.kinds.get(node.kind)
    effective = kinds_module.effective_fields(node, kind) if kind else dict(node.fields)
    return {**_summary(node), "body": node.body, "effective_fields": effective}


def add_node(
    root: Path,
    node_id: str,
    kind: str,
    title: str | None = None,
    body: str = "",
    fields: dict[str, Any] | None = None,
    needs: list[str] | None = None,
    in_: list[str] | None = None,
) -> dict[str, Any]:
    """Create a node; every edge target must already exist.

    @purpose  ops.add_node over MCP, canonical frontmatter and all.
    """
    node = ops.add_node(
        root,
        node_id,
        kind,
        title=title,
        body=body,
        fields=fields,
        needs=tuple(needs or ()),
        in_=tuple(in_ or ()),
        actor="mcp",
    )
    return _summary(node)


def update_node(
    root: Path,
    node_id: str,
    kind: str | None = None,
    title: str | None = None,
    body: str | None = None,
    priority: int | None = None,
    set_fields: dict[str, Any] | None = None,
    unset_fields: list[str] | None = None,
) -> dict[str, Any]:
    """Change kind, title, body, priority, or kind-defined fields.

    @purpose  ops.update_node over MCP; comments in the file survive.
    """
    node = ops.update_node(
        root,
        node_id,
        kind=kind,
        title=title,
        body=body,
        priority=priority,
        set_fields=set_fields,
        unset_fields=tuple(unset_fields or ()),
        actor="mcp",
    )
    return _summary(node)


def remove_node(root: Path, node_id: str, force: bool = False) -> dict[str, Any]:
    """Delete a node; force strips every reference to it first.

    @purpose  ops.remove_node over MCP — a referenced node names its referrers
              instead of dying quietly.
    """
    referrers = ops.remove_node(root, node_id, force=force, actor="mcp")
    return {"removed": node_id, "referrers_stripped": referrers}


def link(
    root: Path,
    src: str,
    needs: str | None = None,
    in_: str | None = None,
    to: str | None = None,
    rel: str = "see-also",
    agents: str | None = None,
    skills: str | None = None,
    trains: str | None = None,
) -> dict[str, Any]:
    """Draw one edge: a dependency, a membership, an annotation, or a mention.

    @purpose  ops.link over MCP, all six kwargs carried through unchanged
              (K36): a needs-edge that would close a cycle is refused with
              the path, and a mention (agents=/skills=/trains=) whose target
              is the wrong kind is refused naming the kind it expected —
              exactly ops.link's own rules, never a second copy of them.
    """
    return _summary(
        ops.link(
            root,
            src,
            needs=needs,
            in_=in_,
            to=to,
            rel=rel,
            agents=agents,
            skills=skills,
            trains=trains,
            actor="mcp",
        )
    )


def unlink(
    root: Path,
    src: str,
    needs: str | None = None,
    in_: str | None = None,
    to: str | None = None,
    agents: str | None = None,
    skills: str | None = None,
    trains: str | None = None,
) -> dict[str, Any]:
    """Remove one edge, mentions included.

    @purpose  ops.unlink over MCP; removing an absent edge errors — agents=/
              skills=/trains= included (K36) — so stale agent state gets
              noticed.
    """
    return _summary(
        ops.unlink(
            root,
            src,
            needs=needs,
            in_=in_,
            to=to,
            agents=agents,
            skills=skills,
            trains=trains,
            actor="mcp",
        )
    )


def rename_node(root: Path, old: str, new: str) -> dict[str, Any]:
    """Move a node to a new id, fixing every referrer and the view layout.

    @purpose  ops.rename_node over MCP; the renamed file's bytes never change.
    """
    return _summary(ops.rename_node(root, old, new, actor="mcp"))


def check(root: Path) -> list[dict[str, str]]:
    """Every finding, errors first.

    @purpose  The same findings the CLI table and (later) the editor panel show.
    """
    plan = Plan.load(root)
    return [finding.model_dump() for finding in plan.check()]


def braid(
    root: Path,
    strategy: str | None = None,
    where: dict[str, str] | None = None,
    from_: str | None = None,
    until: str | None = None,
    in_: str | None = None,
    for_agent: str | None = None,
    diagram: bool | None = None,
    dry: bool = False,
) -> dict[str, Any]:
    """Compile the plan (or a slice) and return the prompt text.

    @purpose  The braid over MCP, with the same slicing vocabulary as the CLI
              (for_agent = --for); warnings ride along instead of going to a
              console.
    """
    result = braid_pipeline(
        Plan.load(root),
        strategy=strategy,
        where=where,
        from_=from_,
        until=until,
        in_=in_,
        for_agent=for_agent,
        diagram=diagram,
        dry=dry,
    )
    return {"text": result.text, "order": result.order, "warnings": result.warnings}


def ready(root: Path, for_agent: str | None = None) -> list[dict[str, Any]]:
    """Nodes whose own status is todo and whose needs are all satisfied.

    @purpose  "What should I work on next?" as one call. A dependency is
              satisfied when it has no status field, or its effective status is
              done, settled, or answered. for_agent narrows the result to
              nodes whose `agents:` key mentions that agent id specifically —
              not `skills:`/`trains:`, which name a capability or a trainer
              rather than "assigned to do this" (PLAN2 §3.3). Validated
              exactly like `braid --for`: a missing or wrong-kind id raises,
              naming it, rather than silently returning an empty list.
    @tags     ready, next-work, for-agent
    """
    plan = Plan.load(root)
    if for_agent is not None:
        validate_for_agent(plan, for_agent)

    def status_of(node: Node) -> str | None:
        """Effective status of a node, or None when its kind has no status.

        @purpose  One status lookup shared by both halves of the readiness rule.
        """
        kind = plan.kinds.get(node.kind)
        effective = kinds_module.effective_fields(node, kind) if kind else dict(node.fields)
        value = effective.get("status")
        return value if isinstance(value, str) else None

    result: list[dict[str, Any]] = []
    for _, node in sorted(plan.nodes.items()):
        if for_agent is not None and for_agent not in node.agents:
            continue
        if status_of(node) != "todo":
            continue
        satisfied = True
        for dep in node.needs:
            target = plan.nodes.get(dep)
            if target is None:
                satisfied = False
                break
            dep_status = status_of(target)
            if dep_status is not None and dep_status not in DONE_VALUES:
                satisfied = False
                break
        if satisfied:
            result.append(_summary(node))
    return result


def crew(root: Path) -> list[dict[str, Any]]:
    """Every agent/skill/reference node: effective fields, trained date, and
    mention counts.

    @purpose  The roster `kumihimo crew` also prints, structured for a
              caller to reason about. Dates travel verbatim, never compared to
              a clock — staleness is the caller's judgment (PLAN2 §3.6).
    @tags     crew, roster
    """
    plan = Plan.load(root)
    return [
        {
            "id": entry.id,
            "kind": entry.kind,
            "title": entry.title,
            "fields": entry.fields,
            "mentions": entry.mentioned_by,
            "consulted_by": entry.consulted_by,
        }
        for entry in crew_module.roster(plan)
    ]
