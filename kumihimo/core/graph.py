"""
@file        kumihimo/core/graph.py
@purpose     Deterministic structure over the plan DAG: the one topological order
             the whole system trusts (Kahn with a sorted ready-heap, ties broken
             by priority then id), cycle extraction that names the path, and
             ancestor/descendant cones for slicing.
@layer       core
@tags        topo-sort, determinism, cycles, kahn, cones
@related     kumihimo/core/validate.py (reports the cycles found here),
             kumihimo/core/errors.py (CycleError carries the path)
@design      PLAN.md §4.1 step 2
"""

from __future__ import annotations

import heapq
from collections import deque

from kumihimo.core.errors import CycleError, KumihimoError
from kumihimo.core.model import Node


def _dependents(nodes: dict[str, Node]) -> dict[str, list[str]]:
    """Reverse adjacency: for each id, the ids that need it.

    @purpose  Kahn walks forward along this; built once, over existing ids only —
              dangling references are validation's finding, not ordering's crash.
    """
    reverse: dict[str, list[str]] = {node_id: [] for node_id in nodes}
    for node in nodes.values():
        for dep in node.needs:
            if dep in nodes:
                reverse[dep].append(node.id)
    return reverse


def braid_order(nodes: dict[str, Node]) -> list[str]:
    """Every node id in the one deterministic topological order.

    @purpose  Same plan in, same order out, on every OS and Python — the invariant
              the byte-identical braid stands on. Ready nodes are taken by
              (priority descending, id ascending); insertion order never matters.
    @tags     topo-sort, determinism
    @related  find_cycle (names the path when this raises CycleError)
    """
    dependents = _dependents(nodes)
    indegree: dict[str, int] = dict.fromkeys(nodes, 0)
    for node in nodes.values():
        for dep in node.needs:
            if dep in nodes:
                indegree[node.id] += 1
    heap = [(-nodes[i].priority, i) for i, degree in indegree.items() if degree == 0]
    heapq.heapify(heap)
    order: list[str] = []
    while heap:
        _, node_id = heapq.heappop(heap)
        order.append(node_id)
        for dependent in dependents[node_id]:
            indegree[dependent] -= 1
            if indegree[dependent] == 0:
                heapq.heappush(heap, (-nodes[dependent].priority, dependent))
    if len(order) < len(nodes):
        cycle = find_cycle(nodes)
        raise CycleError(cycle if cycle else sorted(set(nodes) - set(order)))
    return order


def find_cycle(nodes: dict[str, Node]) -> list[str] | None:
    """The first dependency cycle in deterministic order, as an id path.

    @purpose  "There is a cycle" is useless; "a -> b -> a" is fixable. Starts and
              branches in sorted order so the same plan always names the same
              cycle.
    @tags     cycles
    """
    state: dict[str, int] = dict.fromkeys(nodes, 0)  # 0 unvisited, 1 in path, 2 done
    path: list[str] = []

    def targets(node_id: str) -> list[str]:
        """Existing needs-targets of a node, sorted for determinism.

        @purpose  The one edge iteration order the DFS is allowed to use.
        """
        return sorted(dep for dep in nodes[node_id].needs if dep in nodes)

    for start in sorted(nodes):
        if state[start] != 0:
            continue
        stack: list[tuple[str, list[str]]] = [(start, targets(start))]
        state[start] = 1
        path.append(start)
        while stack:
            node_id, remaining = stack[-1]
            if remaining:
                nxt = remaining.pop(0)
                if state[nxt] == 1:
                    return path[path.index(nxt) :]
                if state[nxt] == 0:
                    state[nxt] = 1
                    path.append(nxt)
                    stack.append((nxt, targets(nxt)))
            else:
                stack.pop()
                path.pop()
                state[node_id] = 2
    return None


def _cone(nodes: dict[str, Node], start: str, forward: bool) -> set[str]:
    """Transitive closure along needs edges, one direction.

    @purpose  Shared walk for ancestors/descendants so they cannot diverge.
    """
    if start not in nodes:
        raise KumihimoError(f"no node '{start}' in the plan")
    edges: dict[str, list[str]]
    if forward:
        edges = {i: [dep for dep in node.needs if dep in nodes] for i, node in nodes.items()}
    else:
        edges = _dependents(nodes)
    seen: set[str] = set()
    queue = deque(edges[start])
    while queue:
        current = queue.popleft()
        if current not in seen:
            seen.add(current)
            queue.extend(edges[current])
    seen.discard(start)
    return seen


def ancestors(nodes: dict[str, Node], node_id: str) -> set[str]:
    """Everything that must come before a node (transitive needs).

    @purpose  The `--until` slice and "what does this depend on, really".
    """
    return _cone(nodes, node_id, forward=True)


def descendants(nodes: dict[str, Node], node_id: str) -> set[str]:
    """Everything downstream of a node (transitive dependents).

    @purpose  The `--from` slice and "what breaks if this changes".
    """
    return _cone(nodes, node_id, forward=False)
