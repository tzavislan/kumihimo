/**
 * @file        frontend/src/containers.ts
 * @purpose     Container math for PLAN2.md §2.3 lens 1: which nodes are
 *              containers and who belongs to which (first `in`-target that
 *              is itself a container — mirrors kumihimo/compile/strategies/
 *              grouped.py's assigned_group, so canvas containment and braid
 *              sections never disagree), n/m done counts, the expanded
 *              container's bounding box, the absolute<->parent-relative
 *              position conversion React Flow's parentId nesting needs
 *              (view.yaml itself stays absolute — App.tsx converts only at
 *              RF-node-construction), and the collapsed-edge reroute/dedupe
 *              pipeline. No React, no DOM, except buildContainerNode, which
 *              returns a ready React Flow node so App.tsx's rebuild effect
 *              doesn't carry the container-specific branch itself.
 *
 *              Shipped path (fix round on K25, risk 1 closed): auto-layout
 *              teaches elk real containment — layout.ts feeds it expanded
 *              containers as compound nodes (their members as `children`,
 *              `elk.hierarchyHandling: INCLUDE_CHILDREN` so cross-container
 *              edges route without lowest-common-ancestor classification on
 *              this side) — so boundingBox below is now the VIEW.YAML-MODE
 *              derivation only: whenever a hand-dragged or hand-edited
 *              position can land a member somewhere elk's own layout never
 *              touched, the container's box still has to be read back off
 *              wherever its members actually are. Pure auto mode uses elk's
 *              own computed compound size instead (App.tsx, via layout.ts's
 *              containerSizes) and never calls boundingBox at all.
 * @layer       frontend
 * @tags        containers, subflows, collapse, elk, hierarchy, react-flow
 * @related     frontend/src/App.tsx (calls every export here once per
 *              payload/render, owns the collapsed-set toggle and drag-
 *              stop's absolute-position lookup),
 *              frontend/src/KumiGroupNode.tsx (the node component
 *              buildContainerNode's data feeds),
 *              frontend/src/edges.ts (buildEdges — containerEdges reroutes
 *              its output rather than duplicating the four-port model),
 *              frontend/src/layout.ts (elk's real hierarchy — the same
 *              containers/assignments/collapsed shapes this mirrors, and
 *              the containerSizes buildContainerNode prefers in auto mode),
 *              frontend/src/derive.ts (memberCounts — "is a container" is
 *              literally memberCounts(node) > 0, reused not recomputed),
 *              frontend/src/lenses.ts (imports resolveEndpoint — Flow/Risk's
 *              "collapsed containers substitute for their members" is the
 *              same rule, K26),
 *              kumihimo/compile/strategies/grouped.py (assigned_group, the
 *              server-side grouping this mirrors for canvas rendering)
 * @design      PLAN2.md §2.3 lens 1, §5 risk 1
 */
import type { Edge, Node } from "@xyflow/react";
import { memberCounts } from "./derive";
import { buildEdges, STATIC_HANDLES } from "./edges";
import type { KumiGroupNodeData } from "./KumiGroupNode";
import { NODE_HEIGHT, NODE_WIDTH } from "./layout";
import type { Payload, PlanNode, Position } from "./types";

const PADDING = 16;
const HEADER_HEIGHT = 32;

export interface ContainerBox {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface Grouping {
  counts: Map<string, number>;
  containers: Set<string>;
  // memberId -> its container id. A container is never itself assigned a
  // parent — single-level nesting only this pass (PLAN2 doesn't ask for
  // milestones-in-milestones, and one stable position per container is
  // most of this spike's actual risk).
  assignments: Map<string, string>;
}

/** Which nodes are containers (any `in`-target of >=1 node) and who belongs
 * to which. Computed together since assignments needs the container set
 * first and every caller wants both. */
export function groupNodes(nodes: PlanNode[]): Grouping {
  const counts = memberCounts(nodes);
  const containers = new Set(
    nodes.filter((node) => (counts.get(node.id) ?? 0) > 0).map((node) => node.id),
  );
  const assignments = new Map<string, string>();
  for (const node of nodes) {
    if (containers.has(node.id)) continue;
    const parent = node.in.find((target) => containers.has(target));
    if (parent) assignments.set(node.id, parent);
  }
  return { counts, containers, assignments };
}

/** Invert assignments: container id -> its member ids. */
export function membersByContainer(assignments: Map<string, string>): Map<string, string[]> {
  const members = new Map<string, string[]>();
  for (const [memberId, containerId] of assignments) {
    const list = members.get(containerId);
    if (list) list.push(memberId);
    else members.set(containerId, [memberId]);
  }
  return members;
}

/** n/m done — done means effective.status resolved to exactly "done"; kinds
 * with no status field at all (risk, ...) simply never count rather than
 * throwing. */
function doneCount(byId: Map<string, PlanNode>, memberIds: string[]): { done: number; total: number } {
  let done = 0;
  for (const id of memberIds) {
    if (byId.get(id)?.effective.status === "done") done += 1;
  }
  return { done, total: memberIds.length };
}

/** The absolute box bounding every member's card plus padding and a header
 * strip, or null when no member has a known position yet (briefly, before
 * the first elk/view.yaml pass resolves). */
export function boundingBox(memberIds: string[], positions: Record<string, Position>): ContainerBox | null {
  let minX = Infinity;
  let minY = Infinity;
  let maxX = -Infinity;
  let maxY = -Infinity;
  for (const id of memberIds) {
    const pos = positions[id];
    if (!pos) continue;
    minX = Math.min(minX, pos.x);
    minY = Math.min(minY, pos.y);
    maxX = Math.max(maxX, pos.x + NODE_WIDTH);
    maxY = Math.max(maxY, pos.y + NODE_HEIGHT);
  }
  if (!Number.isFinite(minX)) return null;
  return {
    x: minX - PADDING,
    y: minY - PADDING - HEADER_HEIGHT,
    width: maxX - minX + PADDING * 2,
    height: maxY - minY + PADDING * 2 + HEADER_HEIGHT,
  };
}

/** child.position = absolute - parent.position — the only place a canvas
 * coordinate is ever relative to anything but the origin; view.yaml and elk
 * both stay absolute. The reverse is never hand-computed: App.tsx's drag-
 * stop reads React Flow's own live internals.positionAbsolute instead of
 * re-deriving it from a parent lookup that could be one render behind. */
export function toRelative(child: Position, parent: Position): Position {
  return { x: child.x - parent.x, y: child.y - parent.y };
}

/** id as the edge/canvas layer should see it: itself, or its container when
 * that container is collapsed. Exported for lenses.ts (K26): Flow's critical
 * path and Risk's descendant shading walk the needs graph with the same
 * substitution, so a collapsed container counts as its hidden members there
 * too, never re-derived a third way. */
export function resolveEndpoint(
  id: string,
  assignments: Map<string, string>,
  collapsed: Set<string>,
): string {
  const parent = assignments.get(id);
  return parent && collapsed.has(parent) ? parent : id;
}

/** Where a jump/select gesture should actually land (Inherited fix A, K26):
 * itself, or its collapsed container when `id` is currently hidden inside
 * one. `hiddenIn` distinguishes a real redirect from the no-op case — App.tsx
 * uses it to decide whether to show the "expand to open it" notice, which
 * resolveEndpoint's plain id-in/id-out shape can't answer on its own. */
export function jumpTarget(
  id: string,
  assignments: Map<string, string>,
  collapsed: Set<string>,
): { targetId: string; hiddenIn: string | null } {
  const parent = assignments.get(id);
  const hiddenIn = parent && collapsed.has(parent) ? parent : null;
  return { targetId: hiddenIn ?? id, hiddenIn };
}

/** Every canvas edge, containers applied: the primary containment `in` edge
 * (member -> its own resolved container) never draws — nesting, or the
 * collapsed chip, already says it, so the dashed membership line PLAN2.md
 * §1's second critique names is gone for exactly the pairs a container now
 * renders. Any endpoint hidden by a collapsed container re-targets to that
 * container's id instead, and a rerouted id deliberately fails edges.ts's
 * parseEdge (a "reroute:" prefix, not needs:/in:/link:) — the edge panel and
 * unlink button must act on the two real nodes a file actually names, never
 * invent a container-to-container link nothing on disk says, so a rerouted
 * edge just isn't clickable for that panel. Multi-edges collapsing onto the
 * same pair dedupe by kind (className) + resolved endpoints; an edge
 * collapsing into itself (both ends the same container) is dropped.
 *
 * A rerouted edge also carries its ORIGINAL endpoints in `data` (Inherited
 * fix B, K25->K26): focus/trace dimming (App.tsx's edges builder) judges an
 * edge by the real ids a file names, not by the container this reroute now
 * visually points at — a hidden member sitting in a focused node's cone must
 * not read as "unrelated" just because its edge got redrawn onto its chip. */
export interface OriginalEndpoints {
  originalSource: string;
  originalTarget: string;
}

export function containerEdges(
  payload: Payload,
  assignments: Map<string, string>,
  collapsed: Set<string>,
): Edge[] {
  const primary = buildEdges(payload).filter(
    (edge) => !edge.id.startsWith("in:") || assignments.get(edge.source) !== edge.target,
  );
  const seen = new Map<string, Edge>();
  for (const edge of primary) {
    const source = resolveEndpoint(edge.source, assignments, collapsed);
    const target = resolveEndpoint(edge.target, assignments, collapsed);
    if (source === target) continue;
    const changed = source !== edge.source || target !== edge.target;
    // sourceHandle/targetHandle are never touched on reroute, changed or
    // not: edges.ts's STATIC_HANDLES ids (in-left/out-right/in-top/out-
    // bottom) are the same four on a container as on a leaf (KumiNode's
    // EdgeHandles, reused verbatim by KumiGroupNode.tsx) — the id names an
    // edge KIND's port, not a specific node, so it's exactly as valid on
    // whichever node ends up as the endpoint. Clearing it to undefined here
    // used to make React Flow silently drop the edge instead of drawing it:
    // a container has two same-type ("source") handles, and RF can't infer
    // which one an undefined sourceHandle means — live-caught reproducing
    // Inherited fix B's own scenario (K26), not a fix B behavior itself.
    const rerouted: Edge = !changed
      ? edge
      : {
          ...edge,
          id: `reroute:${edge.id}=>${source}->${target}`,
          source,
          target,
          data: { originalSource: edge.source, originalTarget: edge.target } satisfies OriginalEndpoints,
        };
    const key = `${rerouted.className ?? ""}:${source}->${target}`;
    if (!seen.has(key)) seen.set(key, rerouted);
  }
  return [...seen.values()];
}

export interface ContainerNodeParams {
  node: PlanNode;
  color: string;
  collapsed: boolean;
  memberIds: string[];
  byId: Map<string, PlanNode>;
  positions: Record<string, Position>;
  // Elk's own computed compound size (layout.ts's containerSizes), present
  // only in pure-auto mode. When set, it — and positions[node.id], elk's own
  // absolute top-left for this compound — govern the box outright;
  // boundingBox is never called. Absent in view.yaml mode (or when a
  // container has no elk entry yet), where a hand-dragged member can land
  // somewhere elk's own layout never touched, so the box must be read back
  // off wherever the members actually are.
  autoSize: { width: number; height: number } | undefined;
  onToggle: () => void;
  className: string | undefined;
  measured: Node["measured"];
}

/** One ready React Flow node for a container, expanded or collapsed — kept
 * here rather than inlined in App.tsx's rebuild effect so that effect stays
 * about orchestration, not container layout. */
export function buildContainerNode(params: ContainerNodeParams): Node {
  const { node, color, collapsed, memberIds, byId, positions, autoSize, onToggle, className, measured } =
    params;
  const { done, total } = doneCount(byId, memberIds);
  let position = positions[node.id] ?? { x: 0, y: 0 };
  let width = NODE_WIDTH;
  let height = NODE_HEIGHT;
  if (!collapsed) {
    if (autoSize) {
      // Pure auto mode: elk already placed this compound's own absolute
      // top-left in `positions` and computed its size from its children —
      // position stays as read above, only the size comes from elk.
      width = autoSize.width;
      height = autoSize.height;
    } else {
      const box = boundingBox(memberIds, positions);
      if (box) {
        position = { x: box.x, y: box.y };
        width = box.width;
        height = box.height;
      }
    }
  }
  const data: KumiGroupNodeData = { node, color, collapsed, done, total, onToggle };
  return {
    id: node.id,
    type: "kumiGroup",
    position,
    width,
    height,
    // Always draggable — React Flow ties its native dblclick detection to
    // the same drag gesture recognizer that powers dragging (confirmed live:
    // draggable:false silently drops onNodeDoubleClick too, breaking
    // "participates in every lens like any node" for the expanded case),
    // so collapsed-only dragging isn't actually available as a narrower
    // option. Dragging an EXPANDED frame is harmless, not just tolerated:
    // this function always re-derives the box from the SAME members whose
    // own absolute positions a frame-drag never touches — so a frame drag
    // (and everything visually riding along with it, its members included,
    // via React Flow's own parentId grouping) snaps the whole group back
    // together on drop, never a partial or corrupted layout.
    draggable: true,
    data,
    // Declared coordinates only for the COLLAPSED case, whose box is always
    // exactly NODE_WIDTH x NODE_HEIGHT — identical to a leaf's, so the same
    // STATIC_HANDLES apply verbatim. Live-caught (K26, reproducing Inherited
    // fix B): without this, React Flow silently drops any edge rerouted
    // onto a collapsed chip instead of drawing it — a container's handles
    // are otherwise DOM-measured (KumiGroupNode's EdgeHandles, percentage-
    // positioned, the right call for an EXPANDED frame's variable box), and
    // an edge whose endpoint has no declared handles needs that measurement
    // to land before its first paint or it never appears at all. An
    // expanded frame's box size is genuinely dynamic (elk or boundingBox),
    // so it keeps relying on measurement — only the fixed-size collapsed
    // case gets the SSR-style shortcut leaves already use.
    handles: collapsed ? STATIC_HANDLES : undefined,
    measured: collapsed ? measured : undefined,
    className,
  };
}
