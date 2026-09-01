/**
 * @file        frontend/src/edges.ts
 * @purpose     The edge model: build every React Flow edge from a payload's
 *              needs/in/link lists, the static four-port handle geometry
 *              those edges (and every node) anchor to, and the reverse
 *              direction — parse an edge id back into its kind and
 *              endpoints, describe it as a sentence, and build the unlink
 *              op envelope for the edge panel's remove button.
 * @layer       frontend
 * @tags        react-flow, edges, ports, ops
 * @related     frontend/src/App.tsx (calls buildEdges per payload, mounts
 *              STATIC_HANDLES on every node, drives the edge panel/tooltip
 *              off parseEdge/edgeSentence/unlinkEnvelope),
 *              frontend/src/derive.ts (nodeTitle, shared with the rest of
 *              the payload-derived helpers),
 *              frontend/src/KumiNode.tsx (EdgeHandles' ids must match
 *              STATIC_HANDLES exactly),
 *              frontend/src/layout.ts (NODE_WIDTH/NODE_HEIGHT the handle
 *              coordinates are computed from),
 *              kumihimo/server/ops_api.py (the unlink envelope's shape)
 * @design      PLAN.md §5.1, PLAN2.md §2.4
 */
import { MarkerType, Position as FlowPosition, type Edge, type NodeHandle } from "@xyflow/react";
import { nodeTitle } from "./derive";
import { NODE_HEIGHT, NODE_WIDTH } from "./layout";
import type { Payload } from "./types";

export type EdgeMode = "needs" | "in" | "link";

// Static handle geometry (React Flow's SSR recipe): with node dimensions and
// handle coordinates declared, edges render without any browser measure pass —
// including in renderers that never composite a frame.
//
// Four handles, one per edge kind, so membership stops fighting dependencies
// for the same two pixels (PLAN2.md §2.4): needs run left/right, in/link run
// top/bottom. Ids are referenced by buildEdges' sourceHandle/targetHandle.
export const STATIC_HANDLES: NodeHandle[] = [
  {
    id: "in-left",
    type: "target",
    position: FlowPosition.Left,
    x: 0,
    y: NODE_HEIGHT / 2,
    width: 6,
    height: 6,
  },
  {
    id: "out-right",
    type: "source",
    position: FlowPosition.Right,
    x: NODE_WIDTH,
    y: NODE_HEIGHT / 2,
    width: 6,
    height: 6,
  },
  {
    id: "in-top",
    type: "target",
    position: FlowPosition.Top,
    x: NODE_WIDTH / 2,
    y: 0,
    width: 6,
    height: 6,
  },
  {
    id: "out-bottom",
    type: "source",
    position: FlowPosition.Bottom,
    x: NODE_WIDTH / 2,
    y: NODE_HEIGHT,
    width: 6,
    height: 6,
  },
];

// Readable-scale closed arrows on the two directional kinds; links stay
// unmarked since they're a bidirectional annotation, not a dependency arrow.
const ARROW_NEEDS = { type: MarkerType.ArrowClosed, width: 18, height: 18, color: "var(--kumi-edge)" };
const ARROW_IN = { type: MarkerType.ArrowClosed, width: 18, height: 18, color: "var(--kumi-edge-in)" };

/** Every React Flow edge for one payload — needs/in/link, skipping any
 * endpoint absent from this payload's nodes (a dangling reference, mid-edit
 * or from a hand-edited file, draws nothing rather than crashing). */
export function buildEdges(payload: Payload): Edge[] {
  const ids = new Set(payload.nodes.map((node) => node.id));
  const edges: Edge[] = [];
  for (const node of payload.nodes) {
    for (const dep of node.needs) {
      if (!ids.has(dep)) continue;
      edges.push({
        id: `needs:${dep}->${node.id}`,
        source: dep,
        sourceHandle: "out-right",
        target: node.id,
        targetHandle: "in-left",
        className: "kumi-edge-needs",
        markerEnd: ARROW_NEEDS,
      });
    }
    for (const group of node.in) {
      if (!ids.has(group)) continue;
      edges.push({
        id: `in:${node.id}->${group}`,
        source: node.id,
        sourceHandle: "out-bottom",
        target: group,
        targetHandle: "in-top",
        className: "kumi-edge-in",
        markerEnd: ARROW_IN,
      });
    }
    for (const link of node.links) {
      if (!ids.has(link.to)) continue;
      edges.push({
        id: `link:${node.id}->${link.to}:${link.rel}`,
        source: node.id,
        sourceHandle: "out-bottom",
        target: link.to,
        targetHandle: "in-top",
        label: link.rel,
        className: "kumi-edge-link",
        // No color/dasharray here: an inline style beats CSS regardless of
        // specificity, which is exactly what silently broke this label in
        // dark mode before — styles.css themes stroke and label via
        // --kumi-edge-link and --xy-edge-label-color instead.
        labelStyle: { fontSize: 10 },
      });
    }
  }
  return edges;
}

// One id format ("kind:from->to[:rel]"), three consumers: the unlink op, the
// hover tooltip sentence, and the edge panel's jump buttons — parsed once so
// they can't drift apart.
export interface EdgeInfo {
  kind: EdgeMode;
  from: string;
  to: string;
  rel?: string;
}

/** Parse an edge id back into its kind and endpoints, or null when it
 * matches none of the three formats buildEdges produces. */
export function parseEdge(edgeId: string): EdgeInfo | null {
  if (edgeId.startsWith("needs:")) {
    const [dep, node] = edgeId.slice(6).split("->");
    return { kind: "needs", from: node, to: dep };
  }
  if (edgeId.startsWith("in:")) {
    const [member, group] = edgeId.slice(3).split("->");
    return { kind: "in", from: member, to: group };
  }
  if (edgeId.startsWith("link:")) {
    const [src, toRel] = edgeId.slice(5).split("->");
    const separator = toRel.indexOf(":");
    const to = separator === -1 ? toRel : toRel.slice(0, separator);
    const rel = separator === -1 ? undefined : toRel.slice(separator + 1);
    return { kind: "link", from: src, to, rel };
  }
  return null;
}

/** "A needs B" / "A is in B" / "A links B (rel)" — titles, not ids. */
export function edgeSentence(payload: Payload, info: EdgeInfo): string {
  const from = nodeTitle(payload, info.from);
  const to = nodeTitle(payload, info.to);
  if (info.kind === "needs") return `${from} needs ${to}`;
  if (info.kind === "in") return `${from} is in ${to}`;
  return `${from} links ${to}${info.rel ? ` (${info.rel})` : ""}`;
}

/** The unlink op envelope for one edge id, or null when the id doesn't
 * parse. */
export function unlinkEnvelope(edgeId: string): Record<string, unknown> | null {
  const info = parseEdge(edgeId);
  if (!info) return null;
  if (info.kind === "needs") return { op: "unlink", src: info.from, needs: info.to };
  if (info.kind === "in") return { op: "unlink", src: info.from, in: info.to };
  return { op: "unlink", src: info.from, to: info.to };
}
