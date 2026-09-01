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
 *              classification needed on this side.
 * @layer       frontend
 * @tags        elkjs, layout, layered, containers, collapse, hierarchy
 * @related     frontend/src/App.tsx (merges these with view.yaml positions;
 *              containerSizes only consulted in pure-auto mode — view.yaml
 *              mode keeps containers.ts's boundingBox derivation instead),
 *              frontend/src/containers.ts (Grouping — the same containers/
 *              assignments/collapsed shapes this mirrors for the hierarchy)
 * @design      PLAN.md §5.1, PLAN2.md §2.3 lens 1
 */
import ELK from "elkjs/lib/elk.bundled.js";
import type { ElkExtendedEdge, ElkNode } from "elkjs";
import type { PlanNode, Position } from "./types";

export const NODE_WIDTH = 210;
export const NODE_HEIGHT = 66;

// Top-heavy for the title bar (KumiGroupNode.tsx's header); left/bottom/
// right just enough that a member card's shadow doesn't touch the frame.
const CONTAINER_PADDING = "[top=44,left=16,bottom=16,right=16]";

const elk = new ELK();

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
