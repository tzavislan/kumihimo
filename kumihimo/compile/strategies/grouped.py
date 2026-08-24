"""
@file        kumihimo/compile/strategies/grouped.py
@purpose     Sections by membership: each in-target becomes a titled section
             introduced by its own node, ungrouped prerequisites lead, ungrouped
             leftovers trail, and sections order topologically by the real
             dependencies between their members. A group-level cycle falls back
             to linear with a warning instead of lying about order.
@layer       compile
@tags        strategies, grouped, membership, sections
@related     kumihimo/compile/strategies/__init__.py (contract),
             kumihimo/core/graph.py (the global order this respects)
@design      PLAN.md §4.2
"""

from __future__ import annotations

import heapq
from collections import deque
from typing import TYPE_CHECKING

from kumihimo.compile.strategies import Section

if TYPE_CHECKING:
    from kumihimo.core.plan import Plan

_LEAD = "\x00lead"
_TAIL = "\x00tail"
_LEAD_TITLE = "Context and prerequisites"
_TAIL_TITLE = "Ungrouped"


def grouped(plan: Plan, ordered: list[str], warnings: list[str]) -> list[Section]:
    """Partition the order into dependency-ordered, membership-titled sections.

    @purpose  What makes a forty-node braid readable: the milestone structure the
              author drew becomes the document structure the agent reads.
    @tags     grouped, sections
    """
    selected = set(ordered)
    nodes = plan.nodes
    group_ids = {
        target for node_id in ordered for target in nodes[node_id].in_ if target in selected
    }

    dependents: dict[str, list[str]] = {node_id: [] for node_id in ordered}
    for node_id in ordered:
        for dep in nodes[node_id].needs:
            if dep in selected:
                dependents[dep].append(node_id)

    def assigned_group(node_id: str) -> str | None:
        """The group a node belongs to, or None when ungrouped.

        @purpose  Group nodes belong to themselves; members follow their first
                  selected in-target, deterministically by authored order.
        """
        if node_id in group_ids:
            return node_id
        for target in nodes[node_id].in_:
            if target in group_ids:
                return target
        return None

    grouped_set = {node_id for node_id in ordered if assigned_group(node_id) is not None}

    def reaches_grouped(node_id: str) -> bool:
        """Whether anything grouped transitively needs this node.

        @purpose  Decides lead vs tail for ungrouped nodes: prerequisites read
                  before the sections that lean on them.
        """
        seen: set[str] = set()
        queue = deque(dependents[node_id])
        while queue:
            current = queue.popleft()
            if current in seen:
                continue
            seen.add(current)
            if current in grouped_set:
                return True
            queue.extend(dependents[current])
        return False

    bucket: dict[str, str] = {}
    for node_id in ordered:
        group = assigned_group(node_id)
        if group is not None:
            bucket[node_id] = group
        else:
            bucket[node_id] = _LEAD if reaches_grouped(node_id) else _TAIL

    buckets = [_LEAD] if any(b == _LEAD for b in bucket.values()) else []
    buckets += sorted(group_ids)
    edges: dict[str, set[str]] = {b: set() for b in buckets}
    indegree: dict[str, int] = dict.fromkeys(buckets, 0)
    for node_id in ordered:
        for dep in nodes[node_id].needs:
            if dep not in selected:
                continue
            source, target = bucket[dep], bucket[node_id]
            if source == target or _TAIL in (source, target):
                continue
            if target not in edges[source]:
                edges[source].add(target)
                indegree[target] += 1

    def sort_key(name: str) -> str:
        """Heap key: the lead pseudo-group outranks every real group id.

        @purpose  Ties break the same way everywhere or the braid isn't stable.
        """
        return "" if name == _LEAD else name

    heap = [sort_key(b) for b in buckets if indegree[b] == 0]
    heapq.heapify(heap)
    key_to_bucket = {sort_key(b): b for b in buckets}
    section_order: list[str] = []
    while heap:
        current = key_to_bucket[heapq.heappop(heap)]
        section_order.append(current)
        for target in sorted(edges[current]):
            indegree[target] -= 1
            if indegree[target] == 0:
                heapq.heappush(heap, sort_key(target))
    if len(section_order) < len(buckets):
        warnings.append(
            "group-level dependency cycle between milestones; falling back to linear sections"
        )
        return [Section(node_ids=list(ordered))]
    if any(b == _TAIL for b in bucket.values()):
        section_order.append(_TAIL)

    sections: list[Section] = []
    for name in section_order:
        members = [i for i in ordered if bucket[i] == name and i not in group_ids]
        if name == _LEAD:
            sections.append(Section(node_ids=members, title=_LEAD_TITLE))
        elif name == _TAIL:
            sections.append(Section(node_ids=members, title=_TAIL_TITLE))
        else:
            sections.append(Section(node_ids=members, title=nodes[name].title, intro_id=name))
    return [s for s in sections if s.node_ids or s.intro_id]
