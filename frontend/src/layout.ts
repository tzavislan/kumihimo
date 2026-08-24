/**
 * @file        frontend/src/layout.ts
 * @purpose     Auto-layout: run elk's layered algorithm over the needs edges
 *              (order-carrying edges only) and return positions per node id.
 * @layer       frontend
 * @tags        elkjs, layout, layered
 * @related     frontend/src/App.tsx (merges these with view.yaml positions)
 * @design      PLAN.md §5.1
 */
import ELK from "elkjs/lib/elk.bundled.js";
import type { PlanNode, Position } from "./types";

export const NODE_WIDTH = 210;
export const NODE_HEIGHT = 66;

const elk = new ELK();

/** Positions for every node, laid out left-to-right along needs edges. */
export async function elkPositions(nodes: PlanNode[]): Promise<Record<string, Position>> {
  const ids = new Set(nodes.map((node) => node.id));
  const graph = {
    id: "root",
    layoutOptions: {
      "elk.algorithm": "layered",
      "elk.direction": "RIGHT",
      "elk.spacing.nodeNode": "40",
      "elk.layered.spacing.nodeNodeBetweenLayers": "90",
    },
    children: nodes.map((node) => ({
      id: node.id,
      width: NODE_WIDTH,
      height: NODE_HEIGHT,
    })),
    edges: nodes.flatMap((node) =>
      node.needs
        .filter((dep) => ids.has(dep))
        .map((dep) => ({ id: `e:${dep}->${node.id}`, sources: [dep], targets: [node.id] })),
    ),
  };
  const laid = await elk.layout(graph);
  const positions: Record<string, Position> = {};
  for (const child of laid.children ?? []) {
    positions[child.id] = { x: Math.round(child.x ?? 0), y: Math.round(child.y ?? 0) };
  }
  return positions;
}
