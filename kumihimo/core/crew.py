"""
@file        kumihimo/core/crew.py
@purpose     The crew roster: every agent/skill/reference node, sorted by kind
             then id, with its effective fields and how many other nodes
             mention it (agents:/skills:/trains: counted per key; consult
             links counted separately for references). One shared computation
             for `kumihimo crew` and the `crew` MCP tool — dates (`trained`,
             `cadence`) ride in the effective fields verbatim, never compared
             to a clock: staleness is a query the caller makes, not something
             this library decides (PLAN2 §3.6).
@layer       core
@tags        crew, roster, mentions, agents, skills, references
@related     kumihimo/core/model.py (the mention keys this counts),
             kumihimo/cli/crew_cmd.py (CLI rendering),
             kumihimo/mcp/tools.py (MCP rendering)
@design      PLAN2.md §3.6, queue item K29
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from kumihimo.core import kinds as kinds_module
from kumihimo.core.plan import Plan

# The three kinds a roster ever lists — everything mentions:/consults: can
# point at (PLAN2 §3.1, §3.7).
CREW_KINDS = ("agent", "skill", "reference")

_MENTION_KEYS = ("agents", "skills", "trains")


@dataclass
class RosterEntry:
    """One crew member's row: identity, effective fields, and who points at it.

    @purpose  Enough for both the CLI table and the MCP tool to render without
              re-walking the plan — mentioned_by never includes zero counts,
              so callers can iterate it directly for a compact display.
    """

    id: str
    kind: str
    title: str
    fields: dict[str, Any]
    mentioned_by: dict[str, int] = field(default_factory=dict)
    consulted_by: int = 0


def roster(plan: Plan) -> list[RosterEntry]:
    """Every agent/skill/reference node, sorted by kind then id.

    @purpose  The one computation `kumihimo crew` and the crew MCP tool both
              render — two passes over the plan (tally mentions, then build
              rows) instead of an O(n^2) scan per crew member.
    @tags     crew, roster
    """
    mention_counts: dict[str, dict[str, int]] = {}
    consult_counts: dict[str, int] = {}
    for node in plan.nodes.values():
        for key in _MENTION_KEYS:
            for target in getattr(node, key):
                counts = mention_counts.setdefault(target, {})
                counts[key] = counts.get(key, 0) + 1
        for link in node.links:
            if link.rel != "consult":
                continue
            target_node = plan.nodes.get(link.to)
            # Matches render.py's *Consult:* rule exactly (PLAN2 §3.7): only
            # a rel=consult link whose target is kind reference is a real
            # consult-link. A rel=consult link to anything else renders as
            # an ordinary See-also entry, so it must not inflate this count.
            if target_node is not None and target_node.kind == "reference":
                consult_counts[link.to] = consult_counts.get(link.to, 0) + 1

    entries: list[RosterEntry] = []
    for node_id in sorted(plan.nodes):
        node = plan.nodes[node_id]
        if node.kind not in CREW_KINDS:
            continue
        kind = plan.kinds.get(node.kind)
        effective = kinds_module.effective_fields(node, kind) if kind else dict(node.fields)
        entries.append(
            RosterEntry(
                id=node_id,
                kind=node.kind,
                title=node.title,
                fields=effective,
                mentioned_by=mention_counts.get(node_id, {}),
                consulted_by=consult_counts.get(node_id, 0),
            )
        )
    entries.sort(key=lambda entry: (entry.kind, entry.id))
    return entries
