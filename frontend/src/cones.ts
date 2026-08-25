/**
 * @file        frontend/src/cones.ts
 * @purpose     Pure graph math over the payload's needs edges: ancestor and
 *              descendant cones (BFS hop-distance) for focus mode, and the
 *              node set lying on any needs-path between two nodes for trace
 *              mode. No React, no DOM — App.tsx turns these sets into style.
 * @layer       frontend
 * @tags        graph, bfs, needs-edges, focus, trace
 * @related     frontend/src/App.tsx (double-click/alt-click handlers call
 *              these and hold the results as view state),
 *              frontend/src/types.ts (PlanNode.needs is the only edge read)
 * @design      PLAN2.md §2.1
 */
import type { PlanNode } from "./types";

/** dependency id -> ids of nodes that list it in their own `needs` — the
 * reverse of PlanNode.needs, built once so descendant BFS doesn't rescan the
 * full node list at every hop. */
function reverseNeeds(nodes: PlanNode[]): Map<string, string[]> {
  const reverse = new Map<string, string[]>();
  for (const node of nodes) {
    for (const dep of node.needs) {
      const list = reverse.get(dep);
      if (list) list.push(node.id);
      else reverse.set(dep, [node.id]);
    }
  }
  return reverse;
}

/** BFS over an adjacency map, returning hop-distance from `start`. `start`
 * itself is never in the result — callers treat the focus/root node as a
 * separate, zero-distance case from its cone. */
function bfs(start: string, adjacency: Map<string, string[]>): Map<string, number> {
  const distance = new Map<string, number>();
  const seen = new Set([start]);
  let frontier = [start];
  let depth = 0;
  while (frontier.length > 0) {
    depth += 1;
    const next: string[] = [];
    for (const id of frontier) {
      for (const neighbor of adjacency.get(id) ?? []) {
        if (seen.has(neighbor)) continue;
        seen.add(neighbor);
        distance.set(neighbor, depth);
        next.push(neighbor);
      }
    }
    frontier = next;
  }
  return distance;
}

/** Upstream cone: every node `id` transitively needs, keyed to hop count. */
export function ancestorsOf(nodes: PlanNode[], id: string): Map<string, number> {
  const forward = new Map(nodes.map((node) => [node.id, node.needs]));
  return bfs(id, forward);
}

/** Downstream cone: every node that transitively needs `id`. */
export function descendantsOf(nodes: PlanNode[], id: string): Map<string, number> {
  return bfs(id, reverseNeeds(nodes));
}

/**
 * Every node id on any needs-path between `a` and `b`.
 *
 * @purpose  A path node is one that is simultaneously downstream of one end
 *           and upstream of the other, so it's the overlap of one node's
 *           descendant cone with the other's ancestor cone. Trace doesn't
 *           know which end is upstream, so both orientations are checked and
 *           unioned; neither connecting yields the empty set.
 */
export function pathsBetween(nodes: PlanNode[], a: string, b: string): Set<string> {
  const onPath = new Set<string>();
  const forward = (from: string, to: string) => {
    const downstream = descendantsOf(nodes, from);
    if (!downstream.has(to)) return;
    const upstream = ancestorsOf(nodes, to);
    onPath.add(from);
    onPath.add(to);
    for (const id of downstream.keys()) {
      if (upstream.has(id)) onPath.add(id);
    }
  };
  forward(a, b);
  forward(b, a);
  return onPath;
}
