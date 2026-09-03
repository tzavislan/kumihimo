/**
 * @file        frontend/src/layout.ts
 * @purpose     Auto-layout: run elk's layered algorithm over the needs edges
 *              (order-carrying edges only) and return positions per node id,
 *              plus computed sizes for expanded containers. Containers are
 *              real elk hierarchy now, not a retroactive box (fix round on
 *              K25 — the shipped path, not a fallback): an expanded
 *              container becomes a compound elk node whose members are its
 *              `children`, sized and positioned by elk itself from `elk.
 *              padding` plus its children's own layout; a collapsed
 *              container is a plain leaf at chip size, its (hidden) members
 *              excluded entirely — same substitution containers.ts's
 *              containerEdges does for the canvas's own edges. `elk.
 *              hierarchyHandling: INCLUDE_CHILDREN` lets every needs edge be
 *              declared once, flat, at the root, referencing real node ids
 *              regardless of which compound they're nested in — elk routes
 *              cross-container edges itself, no lowest-common-ancestor
 *              classification needed on this side. elkjs itself is a
 *              dynamic import (K34, getElk below): its bundled entry is
 *              ~1.4MB minified, so it stays out of the initial bundle and is
 *              fetched only the first time a layout actually runs — a
 *              module-level cached promise means every call after the first
 *              awaits the same settled import rather than re-fetching.
 *              hasLayoutGaps is the other K34 half: a plain, elk-free walk
 *              callers use to skip calling into this file at all when
 *              view.yaml already positions everything, which is what keeps
 *              a fully-positioned plan's cold load from touching elk (or its
 *              chunk) in the first place.
 * @layer       frontend
 * @tags        elkjs, layout, layered, containers, collapse, hierarchy,
 *              layout-mode, re-layout, centroid, lazy-load, dynamic-import
 * @related     frontend/src/App.tsx (merges these with view.yaml positions,
 *              calling hasLayoutGaps below FIRST so a fully-positioned
 *              plan's cold load skips this file's elk call — and its
 *              dynamic import — entirely; containerSizes only consulted in
 *              pure-auto mode — view.yaml mode keeps containers.ts's
 *              boundingBox derivation instead),
 *              frontend/src/containers.ts (Grouping — the same containers/
 *              assignments/collapsed shapes this mirrors for the hierarchy;
 *              also relayoutScope, which resolves the scope
 *              elkBranchPositions below lays out),
 *              frontend/src/lanes.ts (the Lanes layoutMode alternative to
 *              elkPositions — reuses NODE_WIDTH/NODE_HEIGHT and
 *              LayoutContext from here rather than redeclaring them)
 * @design      PLAN.md §5.1, PLAN2.md §2.3 lens 1, §2.3-2.5 (layoutMode,
 *              Re-layout branch, K27), queue item K34 (elk lazy-load)
 */
import type { ELK, ElkExtendedEdge, ElkNode } from "elkjs";
import type { PlanNode, Position } from "./types";

export const NODE_WIDTH = 210;
export const NODE_HEIGHT = 66;

// Which position source is currently driving the canvas (PLAN2.md §2.3-2.5,
// K27): "view" is view.yaml-with-elk-filling-gaps (today's only mode before
// K27); "auto" is pure elk, exactly as the old useViewLayout=false meant;
// "lanes" is lanes.ts's depth-lanes algorithm. All three are App.tsx state,
// never persisted — the mode itself is view state, same as the positions it
// produces.
export type LayoutMode = "view" | "auto" | "lanes";

// Top-heavy for the title bar (KumiGroupNode.tsx's header); left/bottom/
// right just enough that a member card's shadow doesn't touch the frame.
const CONTAINER_PADDING = "[top=44,left=16,bottom=16,right=16]";

// K34: the promise itself is the cache — every call after the first awaits
// this same settled promise instead of re-importing or re-constructing.
// Only elkPositions/elkBranchPositions below ever call this, and only when
// they actually run, so a caller that skips them via hasLayoutGaps never
// pulls elkjs's chunk over the network at all.
let elkPromise: Promise<ELK> | null = null;
function getElk(): Promise<ELK> {
  if (!elkPromise) {
    elkPromise = import("elkjs/lib/elk.bundled.js").then((mod) => new mod.default());
  }
  return elkPromise;
}

export interface LayoutContext {
  collapsed: Set<string>;
  containers: Set<string>;
  // memberId -> its container id (containers.ts's Grouping.assignments).
  assignments: Map<string, string>;
}

export interface ContainerSize {
  width: number;
  height: number;
}

export interface AutoLayoutResult {
  // Absolute position for every node elk placed — loose nodes, collapsed-
  // chip containers, expanded-container compounds themselves, AND their
  // members (elk returns member coordinates parent-relative; converted to
  // absolute here, one level, before this map is built).
  positions: Record<string, Position>;
  // Elk's own computed width/height for each EXPANDED container — the auto-
  // mode size (App.tsx uses containers.ts's boundingBox instead whenever
  // view.yaml positions are in play, since a hand-dragged member can land
  // somewhere elk's own layout never touched).
  containerSizes: Record<string, ContainerSize>;
}

/** Positions (and, for expanded containers, sizes) for every node, laid out
 * left-to-right along needs edges — hierarchically, when `context` names any
 * containers: an expanded container is a compound elk node whose children
 * are its members; a collapsed one is a plain leaf at chip size with its
 * members excluded. */
export async function elkPositions(nodes: PlanNode[], context?: LayoutContext): Promise<AutoLayoutResult> {
  const ids = new Set(nodes.map((node) => node.id));
  const containers = context?.containers ?? new Set<string>();
  const assignments = context?.assignments ?? new Map<string, string>();
  const collapsed = context?.collapsed ?? new Set<string>();

  // id as elk should see it: itself, or its container when that container is
  // collapsed (a collapsed container substitutes for its now-hidden
  // members) — needed for edges only; membership below is walked directly.
  const elkId = (id: string): string => {
    const parent = assignments.get(id);
    return parent && collapsed.has(parent) ? parent : id;
  };

  const membersByContainer = new Map<string, string[]>();
  for (const [memberId, containerId] of assignments) {
    const list = membersByContainer.get(containerId);
    if (list) list.push(memberId);
    else membersByContainer.set(containerId, [memberId]);
  }

  const rootChildren: ElkNode[] = [];
  for (const node of nodes) {
    const parent = assignments.get(node.id);
    if (parent) {
      // A hidden member of a collapsed container is excluded entirely (the
      // container substitutes for it); a member of an expanded container is
      // placed as that container's own elk child below, not here.
      continue;
    }
    if (containers.has(node.id)) {
      if (collapsed.has(node.id)) {
        rootChildren.push({ id: node.id, width: NODE_WIDTH, height: NODE_HEIGHT });
      } else {
        const memberIds = (membersByContainer.get(node.id) ?? []).filter((id) => ids.has(id));
        rootChildren.push({
          id: node.id,
          layoutOptions: { "elk.padding": CONTAINER_PADDING },
          children: memberIds.map((id) => ({ id, width: NODE_WIDTH, height: NODE_HEIGHT })),
        });
      }
      continue;
    }
    rootChildren.push({ id: node.id, width: NODE_WIDTH, height: NODE_HEIGHT });
  }

  const edgeIds = new Set<string>();
  const edges: ElkExtendedEdge[] = [];
  for (const node of nodes) {
    for (const dep of node.needs) {
      if (!ids.has(dep)) continue;
      const source = elkId(dep);
      const target = elkId(node.id);
      if (source === target) continue;
      const key = `${source}->${target}`;
      if (edgeIds.has(key)) continue;
      edgeIds.add(key);
      edges.push({ id: `e:${key}`, sources: [source], targets: [target] });
    }
  }

  const graph: ElkNode = {
    id: "root",
    layoutOptions: {
      "elk.algorithm": "layered",
      "elk.direction": "RIGHT",
      "elk.hierarchyHandling": "INCLUDE_CHILDREN",
      "elk.spacing.nodeNode": "40",
      "elk.layered.spacing.nodeNodeBetweenLayers": "90",
    },
    children: rootChildren,
    edges,
  };

  const elk = await getElk();
  const laid = await elk.layout(graph);
  const positions: Record<string, Position> = {};
  const containerSizes: Record<string, ContainerSize> = {};
  for (const child of laid.children ?? []) {
    const x = Math.round(child.x ?? 0);
    const y = Math.round(child.y ?? 0);
    positions[child.id] = { x, y };
    if (child.children && child.children.length > 0) {
      containerSizes[child.id] = {
        width: Math.round(child.width ?? NODE_WIDTH),
        height: Math.round(child.height ?? NODE_HEIGHT),
      };
      // Single level: elk returns a compound's children relative to the
      // compound's own origin, so absolute is just one addition each.
      for (const member of child.children) {
        positions[member.id] = { x: x + Math.round(member.x ?? 0), y: y + Math.round(member.y ?? 0) };
      }
    }
  }
  return { positions, containerSizes };
}

/**
 * True when SOME node view.yaml mode would actually render has no known
 * position yet in `layout` — a freshly added node, or a plan with no
 * view.yaml at all. False means view.yaml already positions everything
 * elkPositions above would otherwise be asked to fill in, so App.tsx skips
 * calling it (and therefore skips getElk's dynamic import) entirely on a
 * cold load: the whole point of K34's lazy-load is defeated if "fill gaps"
 * still runs elk unconditionally on every load just to be overridden by
 * view.yaml afterward, so this walks the SAME node set elkPositions's own
 * rootChildren loop does, but synchronously and elk-free, purely to answer
 * "is there actually a gap."
 *
 * A hidden member of a collapsed container needs no position (excluded from
 * rendering entirely, same as elkPositions treats it) and neither does an
 * EXPANDED container's own id — containers.ts's boundingBox derives its box
 * from its members' positions in view.yaml mode, never consulting the
 * container's own entry unless no member has landed yet, which can't happen
 * once every member itself passes this same check. Every other visible id
 * — loose nodes, collapsed containers as themselves, and an expanded
 * container's own members — needs its own entry.
 */
export function hasLayoutGaps(
  nodes: PlanNode[],
  layout: Record<string, Position>,
  context?: LayoutContext,
): boolean {
  const containers = context?.containers ?? new Set<string>();
  const assignments = context?.assignments ?? new Map<string, string>();
  const collapsed = context?.collapsed ?? new Set<string>();
  for (const node of nodes) {
    const parent = assignments.get(node.id);
    if (parent) {
      if (!collapsed.has(parent) && !(node.id in layout)) return true;
      continue;
    }
    if (containers.has(node.id) && !collapsed.has(node.id)) continue;
    if (!(node.id in layout)) return true;
  }
  return false;
}

/**
 * Re-layout branch (PLAN2.md §2.3-2.5, K27): run elk over ONLY `scope` — a
 * flat layered subgraph, no container hierarchy (scope members are leaves
 * regardless of whether one happens to be a container id itself; the common
 * case is a container's own members, already flat, and containers.ts's
 * relayoutScope never puts a container's own members-of-members in scope
 * since containment is single-level) — using only `needs` edges between two
 * scope members, same restriction elkPositions above already applies to the
 * full graph. The raw result is then translated as a whole so its centroid
 * lands exactly on the scope's PREVIOUS centroid (`currentPositions`, read
 * before this call): elk's own subgraph layout starts counting from an
 * arbitrary near-{0,0} origin with no memory of where the scope used to sit
 * on THIS canvas, so using it as-is would teleport the branch to a corner.
 */
export async function elkBranchPositions(
  nodes: PlanNode[],
  scope: Set<string>,
  currentPositions: Record<string, Position>,
): Promise<Record<string, Position>> {
  const scoped = nodes.filter((node) => scope.has(node.id));
  const ids = new Set(scoped.map((node) => node.id));
  const edgeIds = new Set<string>();
  const edges: ElkExtendedEdge[] = [];
  for (const node of scoped) {
    for (const dep of node.needs) {
      if (!ids.has(dep) || dep === node.id) continue;
      const key = `${dep}->${node.id}`;
      if (edgeIds.has(key)) continue;
      edgeIds.add(key);
      edges.push({ id: `e:${key}`, sources: [dep], targets: [node.id] });
    }
  }
  const graph: ElkNode = {
    id: "root",
    layoutOptions: {
      "elk.algorithm": "layered",
      "elk.direction": "RIGHT",
      "elk.spacing.nodeNode": "40",
      "elk.layered.spacing.nodeNodeBetweenLayers": "90",
    },
    children: scoped.map((node) => ({ id: node.id, width: NODE_WIDTH, height: NODE_HEIGHT })),
    edges,
  };
  const elk = await getElk();
  const laid = await elk.layout(graph);
  const raw: Record<string, Position> = {};
  for (const child of laid.children ?? []) {
    raw[child.id] = { x: Math.round(child.x ?? 0), y: Math.round(child.y ?? 0) };
  }

  const before = centroidOf(scope, currentPositions);
  const after = centroidOf(new Set(Object.keys(raw)), raw);
  if (!before || !after) return raw;
  const dx = before.x - after.x;
  const dy = before.y - after.y;
  const translated: Record<string, Position> = {};
  for (const [id, pos] of Object.entries(raw)) {
    translated[id] = { x: Math.round(pos.x + dx), y: Math.round(pos.y + dy) };
  }
  return translated;
}

/** The average x/y of every id in `ids` that has a known position, or null
 * when none do — callers bail to the untranslated result rather than divide
 * by zero. */
function centroidOf(ids: Set<string>, positions: Record<string, Position>): Position | null {
  let sumX = 0;
  let sumY = 0;
  let count = 0;
  for (const id of ids) {
    const pos = positions[id];
    if (!pos) continue;
    sumX += pos.x;
    sumY += pos.y;
    count += 1;
  }
  return count > 0 ? { x: sumX / count, y: sumY / count } : null;
}
