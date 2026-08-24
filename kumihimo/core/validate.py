"""
@file        kumihimo/core/validate.py
@purpose     Every rule `check` enforces, as findings: unknown/missing kinds,
             field-schema breaches, dangling edges, the cycle (with its path),
             orphans, dependencies on still-open nodes, and empty bodies.
             Deterministic order: errors first, then warnings, each sorted.
@layer       core
@tags        validation, findings, rules, check
@related     kumihimo/core/kinds.py (field validation per node),
             kumihimo/core/graph.py (cycle detection),
             kumihimo/core/plan.py (Plan.check calls this)
@design      PLAN.md §3.4
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from kumihimo.core import graph
from kumihimo.core import kinds as kinds_module
from kumihimo.core.model import Finding, Node

if TYPE_CHECKING:
    from kumihimo.core.plan import Plan


def _edge_targets(node: Node) -> list[tuple[str, str]]:
    """Every (edge-kind, target) reference a node makes.

    @purpose  One list so the dangling-reference rule cannot miss an edge kind.
    """
    references = [("needs", dep) for dep in node.needs]
    references += [("in", group) for group in node.in_]
    references += [("links", link.to) for link in node.links]
    return references


def _check_node(plan: Plan, node: Node, findings: list[Finding]) -> None:
    """Per-node rules: kind, fields, dangling references, empty body.

    @purpose  Everything checkable without looking at the rest of the graph.
    """
    if not node.kind:
        findings.append(Finding(level="error", where=node.id, message="node has no kind"))
    elif node.kind not in plan.kinds:
        known = ", ".join(sorted(plan.kinds)) or "none defined"
        message = f"unknown kind '{node.kind}' (this plan defines: {known})"
        findings.append(Finding(level="error", where=node.id, message=message))
    else:
        findings.extend(kinds_module.validate_fields(node, plan.kinds[node.kind]))
    for edge_kind, target in _edge_targets(node):
        if target not in plan.nodes:
            message = f"'{edge_kind}' target '{target}' does not exist"
            findings.append(Finding(level="error", where=node.id, message=message))
    if not node.body.strip():
        findings.append(Finding(level="warning", where=node.id, message="empty body"))


def _check_graph(plan: Plan, findings: list[Finding]) -> None:
    """Whole-graph rules: the cycle, orphans, dependencies on open nodes.

    @purpose  The rules that only exist because nodes relate to each other.
    """
    nodes = plan.nodes
    cycle = graph.find_cycle(nodes)
    if cycle:
        rendered = " -> ".join([*cycle, cycle[0]])
        findings.append(
            Finding(level="error", where=cycle[0], message=f"dependency cycle: {rendered}")
        )
    referenced: set[str] = set()
    for node in nodes.values():
        referenced.update(target for _, target in _edge_targets(node))
    for node_id, node in nodes.items():
        connected = bool(node.needs or node.in_ or node.links) or node_id in referenced
        if not connected:
            message = "orphan: no edges in or out"
            findings.append(Finding(level="warning", where=node_id, message=message))
    for node in nodes.values():
        for dep in node.needs:
            target = nodes.get(dep)
            if target is None or target.kind not in plan.kinds:
                continue
            effective = kinds_module.effective_fields(target, plan.kinds[target.kind])
            if effective.get("status") == "open":
                message = f"depends on '{dep}', which is still open"
                findings.append(Finding(level="warning", where=node.id, message=message))


def check(plan: Plan) -> list[Finding]:
    """All findings for a plan: load findings plus every rule, errors first.

    @purpose  The single validation answer every surface renders — CLI table,
              editor panel, MCP tool — deterministic to the byte.
    @tags     check, findings
    """
    findings = list(plan.load_findings)
    for node_id in sorted(plan.nodes):
        _check_node(plan, plan.nodes[node_id], findings)
    _check_graph(plan, findings)
    return sorted(findings, key=lambda f: (f.level != "error", f.where, f.message))
