/**
 * @file        frontend/src/canvasBuild.ts
 * @purpose     Turn one payload plus the current view state into React
 *              Flow's nodes and edges arrays — the two bodies App.tsx's
 *              nodes-rebuild effect and edges memo used to carry directly,
 *              moved out purely to keep App.tsx under CONVENTIONS.md's line
 *              cap (K26). buildCanvasNodes places containers first (parent-
 *              before-child, React Flow's own requirement), composes each
 *              node's className (cone/halo/lens precedence) via derive.ts and
 *              lenses.ts, and syncs React Flow's native `selected` to the
 *              app's own selectedId (Inherited fix A, K26 — it must never
 *              drift, which is exactly what let the sidebar detach from the
 *              canvas after a keyboard/palette jump before this).
 *              buildCanvasEdges reroutes/dedupes via containers.ts, then
 *              dims by focus/trace (judging each edge by its ORIGINAL
 *              endpoints when containers.ts rerouted it — Inherited fix B) or
 *              bolds/faints by the Flow lens's critical path.
 * @layer       frontend
 * @tags        react-flow, nodes, edges, containers, lenses, halos, selection
 * @related     frontend/src/App.tsx (the sole caller, once each inside its
 *              nodes-rebuild effect and edges memo),
 *              frontend/src/containers.ts (buildContainerNode, Grouping,
 *              containerEdges, OriginalEndpoints),
 *              frontend/src/derive.ts (coneClassName, haloClassName, colorFor,
 *              acceptanceList, findingHalos, FocusState/TraceState),
 *              frontend/src/lenses.ts (lensNodeClasses, flowEdgeClassName,
 *              LensContext, FlowResult)
 * @design      PLAN2.md §2.1-2.3, Inherited fixes A and B (K26)
 */
import type { Edge, Node } from "@xyflow/react";
import {
  buildContainerNode,
  containerEdges,
  membersByContainer,
  toRelative,
  type Grouping,
  type OriginalEndpoints,
} from "./containers";
import {
  acceptanceList,
  colorFor,
  coneClassName,
  findingHalos,
  haloClassName,
  type FocusState,
  type TraceState,
} from "./derive";
import { STATIC_HANDLES } from "./edges";
import type { KumiNodeData, ZoomTier } from "./KumiNode";
import { NODE_HEIGHT, NODE_WIDTH, type ContainerSize } from "./layout";
import { flowEdgeClassName, lensNodeClasses, type FlowResult, type LensContext } from "./lenses";
import type { Payload, Position } from "./types";

export interface BuildCanvasNodesParams {
  payload: Payload;
  positions: Record<string, Position>;
  grouping: Grouping;
  collapsedSet: Set<string>;
  focus: FocusState | null;
  trace: TraceState | null;
  tier: ZoomTier;
  selectedId: string | null;
  // Whether to size an EXPANDED container from layout.ts's elk-computed
  // containerAutoSizes (pure-auto layoutMode only, K27 — renamed from
  // useViewLayout when a third layoutMode, Lanes, made the old inverted
  // "unless view.yaml" phrasing wrong) or fall back to boundingBox.
  useElkSizes: boolean;
  containerAutoSizes: Record<string, ContainerSize>;
  lensCtx: LensContext;
  previous: Node[];
  onToggleCollapse: (id: string) => void;
}

/** The full RF nodes array for one render — see the file header. */
export function buildCanvasNodes(params: BuildCanvasNodesParams): Node[] {
  const {
    payload,
    positions,
    grouping,
    collapsedSet,
    focus,
    trace,
    tier,
    selectedId,
    useElkSizes,
    containerAutoSizes,
    lensCtx,
    previous,
    onToggleCollapse,
  } = params;
  const halos = findingHalos(payload.nodes, payload.findings);
  const members = membersByContainer(grouping.assignments);
  const byId = new Map(payload.nodes.map((node) => [node.id, node]));
  const byOldId = new Map(previous.map((node) => [node.id, node]));
  const built: Node[] = [];

  for (const id of grouping.containers) {
    const containerNode = byId.get(id);
    if (!containerNode) continue;
    const collapsed = collapsedSet.has(id);
    const memberIds = members.get(id) ?? [];
    const halo = haloClassName(id, halos);
    const className =
      [
        coneClassName(id, focus, trace, collapsed ? memberIds : undefined),
        lensNodeClasses(id, containerNode, halo, lensCtx),
      ]
        .filter(Boolean)
        .join(" ") || undefined;
    built.push({
      ...buildContainerNode({
        node: containerNode,
        color: colorFor(payload, containerNode),
        collapsed,
        memberIds,
        byId,
        positions,
        autoSize: useElkSizes ? containerAutoSizes[id] : undefined,
        onToggle: () => onToggleCollapse(id),
        className,
        measured: byOldId.get(id)?.measured,
      }),
      selected: id === selectedId,
    });
  }

  const containerPosition = new Map(built.map((node) => [node.id, node.position]));
  for (const node of payload.nodes) {
    if (grouping.containers.has(node.id)) continue;
    const old = byOldId.get(node.id);
    const parentId = grouping.assignments.get(node.id);
    const hidden = parentId ? collapsedSet.has(parentId) : false;
    const parentPos = parentId ? containerPosition.get(parentId) : undefined;
    const absolute = positions[node.id] ?? { x: 0, y: 0 };
    const data: KumiNodeData = {
      node,
      color: colorFor(payload, node),
      tier,
      memberCount: grouping.counts.get(node.id) ?? 0,
      acceptance: acceptanceList(node),
    };
    const halo = haloClassName(node.id, halos);
    built.push({
      id: node.id,
      type: "kumi",
      // Absolute stays the truth everywhere except this one conversion
      // (containers.ts's toRelative): a member of an EXPANDED container
      // renders parent-relative, per React Flow's own parentId contract.
      position: parentPos && !hidden ? toRelative(absolute, parentPos) : absolute,
      data,
      width: NODE_WIDTH,
      height: NODE_HEIGHT,
      handles: STATIC_HANDLES,
      measured: old?.measured,
      hidden,
      parentId: !hidden ? parentId : undefined,
      extent: !hidden && parentId ? "parent" : undefined,
      selected: node.id === selectedId,
      className:
        [coneClassName(node.id, focus, trace), lensNodeClasses(node.id, node, halo, lensCtx)]
          .filter(Boolean)
          .join(" ") || undefined,
    });
  }
  return built;
}

export interface BuildCanvasEdgesParams {
  payload: Payload;
  grouping: Grouping;
  collapsedSet: Set<string>;
  focus: FocusState | null;
  trace: TraceState | null;
  flow: FlowResult | null;
}

/**
 * The full RF edges array for one render: containerEdges' reroute/dedupe,
 * then EITHER focus/trace dimming (full strength only when both of an
 * edge's ORIGINAL endpoints — Inherited fix B — are in the highlighted set)
 * OR, when the Flow lens is active and neither lens is suspended, its
 * critical-path bold/faint split. Never both at once: focus/trace suspends
 * lens emphasis (PLAN2.md §2.3), so `flow` is already null whenever
 * `focus`/`trace` is non-null (App.tsx's computeLensContext call site).
 */
export function buildCanvasEdges(params: BuildCanvasEdgesParams): Edge[] {
  const { payload, grouping, collapsedSet, focus, trace, flow } = params;
  const built = containerEdges(payload, grouping.assignments, collapsedSet);
  const highlighted = focus
    ? new Set([focus.id, ...focus.ancestors.keys(), ...focus.descendants.keys(), ...(focus.members ?? [])])
    : (trace?.nodes ?? null);

  return built.map((edge) => {
    const className = edge.className ?? "";
    if (highlighted) {
      const data = edge.data as OriginalEndpoints | undefined;
      const from = data?.originalSource ?? edge.source;
      const to = data?.originalTarget ?? edge.target;
      const full = highlighted.has(from) && highlighted.has(to);
      return { ...edge, className: `${className} ${full ? "" : "kumi-edge-dim"}`.trim() };
    }
    if (flow) {
      const isNeeds = className.includes("kumi-edge-needs");
      const flowClass = flowEdgeClassName(edge.source, edge.target, isNeeds, flow);
      return { ...edge, className: `${className} ${flowClass}`.trim() };
    }
    return edge;
  });
}
