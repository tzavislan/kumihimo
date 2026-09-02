"""
@file        kumihimo/core/validate.py
@purpose     Every rule `check` enforces, as findings: unknown/missing kinds,
             field-schema breaches, dangling edges (needs/in/links and the
             three mention keys), wrong-kind mention targets, dangling `@id`
             prose mentions (read-only, PLAN2 §3.2), the cycle (with its
             path), orphans, dependencies on still-open nodes, and empty
             bodies. Deterministic order: errors first, then warnings, each
             sorted.
@layer       core
@tags        validation, findings, rules, check, mentions
@related     kumihimo/core/kinds.py (field validation per node),
             kumihimo/core/graph.py (cycle detection),
             kumihimo/core/plan.py (Plan.check calls this)
@design      PLAN.md §3.4, PLAN2.md §3.1-3.2
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from kumihimo.core import graph
from kumihimo.core import kinds as kinds_module
from kumihimo.core.model import MENTION_KINDS, Finding, Node

if TYPE_CHECKING:
    from kumihimo.core.plan import Plan

# One @id prose mention, e.g. "hand this to @wright" or a bulleted "- @wright".
# The id shape mirrors SLUG_RE loosely (namespace segments aren't required to
# start alnum — a deliberately simple token match, not a second slug parser).
# The boundary requires start-of-line or a preceding whitespace character —
# which, as a side effect, also rejects any preceding alphanumeric, so
# "user@example.com" typed in prose does not match. It is not a Markdown
# parser: an @token that happens to open a line inside a fenced code sample
# (a Python decorator, say) is indistinguishable from a real mention and will
# still be scanned. That imprecision is accepted, not fixed — see
# docs/reference/formats.md.
MENTION_RE = re.compile(r"(?:^|(?<=\s))@([a-z0-9][a-z0-9-]*(?:/[a-z0-9-]+)*)", re.MULTILINE)


def scan_mentions(body: str) -> list[str]:
    """Every @id token in a node body, in the order they appear.

    @purpose  The read-only half of mentions (PLAN2 §3.2): bodies are only
              ever scanned, never rewritten — this function has no caller that
              writes its result back to a file.
    @tags     mentions, prose, read-only
    """
    return [match.group(1) for match in MENTION_RE.finditer(body)]


def _edge_targets(node: Node) -> list[tuple[str, str]]:
    """Every (edge-kind, target) reference a node makes.

    @purpose  One list so the dangling-reference and orphan-connectivity rules
              cannot miss an edge kind — needs/in/links plus the three
              mentions, all real edges; @id prose mentions are not among them
              (they are soft references, scanned separately).
    """
    references = [("needs", dep) for dep in node.needs]
    references += [("in", group) for group in node.in_]
    references += [("links", link.to) for link in node.links]
    references += [("agents", target) for target in node.agents]
    references += [("skills", target) for target in node.skills]
    references += [("trains", target) for target in node.trains]
    return references


def _check_mention_kinds(plan: Plan, node: Node, findings: list[Finding]) -> None:
    """A mention target's kind must match its key, once the target and its
    kind both resolve.

    @purpose  Mentions are typed edges (PLAN2 §3.2): pointing `agents:` at a
              task is a different mistake from a dangling id, and gets its own
              message. Skipped when the target is dangling (already reported)
              or its own kind is unknown (that node's problem, not this edge's).
    """
    for key, expected in MENTION_KINDS.items():
        for target in getattr(node, key):
            target_node = plan.nodes.get(target)
            if target_node is None or target_node.kind not in plan.kinds:
                continue
            if target_node.kind not in expected:
                wanted = " or ".join(expected)
                message = f"'{key}' target '{target}' is kind {target_node.kind}, expected {wanted}"
                findings.append(Finding(level="error", where=node.id, message=message))


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
    _check_mention_kinds(plan, node, findings)
    for mentioned in sorted(set(scan_mentions(node.body))):
        if mentioned not in plan.nodes:
            message = f"body mentions '@{mentioned}' but no node '{mentioned}' exists"
            findings.append(Finding(level="warning", where=node.id, message=message))
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
        has_edge = node.needs or node.in_ or node.links or node.agents or node.skills or node.trains
        connected = bool(has_edge) or node_id in referenced
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
