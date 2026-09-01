/**
 * @file        frontend/src/lanes.ts
 * @purpose     The Lanes layout option (PLAN2.md §2.3-2.5, K27; restructured
 *              in the K27 fix round after critic9 found two container
 *              frames/headers landing pixel-identical and a collapsed chip
 *              swallowed under a neighboring frame — screenshots lanes.png/
 *              lanes-collapsed.png). One column per node's NEEDS-DEPTH
 *              (longest dependency-chain distance from a root), but laid
 *              out in per-container vertical BANDS rather than one flat
 *              global stack: every container that currently has visible
 *              members gets its own band — a contiguous Y range reserved
 *              across every column its members touch, tall enough for the
 *              busiest one plus a header allowance — and every ungrouped
 *              node or collapsed-container chip shares one more band,
 *              stacked last. Bands never overlap by construction, so two
 *              container frames (or a frame and a chip) landing on the same
 *              pixels is impossible regardless of how needs edges happen to
 *              interleave columns — the flat "y by (group, id)" scheme this
 *              replaced could not make that guarantee, and didn't.
 *
 *              The tradeoff, stated once here rather than left implicit:
 *              LANES TRADES VERTICAL COMPACTNESS FOR GUARANTEED SEPARATION.
 *              A band reserves its single busiest column's height across
 *              EVERY column it spans, so a container with one crowded
 *              column and several sparse ones leaves visible empty space
 *              beside the sparse ones — deliberate, not a bug, the same way
 *              a spread-out container's frame bounding empty space already
 *              is (docs/howto/editor.md's Layout section).
 * @layer       frontend
 * @tags        layout, lanes, needs-depth, longest-path, containers, bands,
 *              collision-avoidance
 * @related     frontend/src/layout.ts (elk's own layered algorithm — the
 *              Auto option this sits beside; NODE_WIDTH/NODE_HEIGHT and the
 *              LayoutContext shape this reuses),
 *              frontend/src/containers.ts (resolveEndpoint — the collapsed-
 *              container substitution reused for depth; boundingBox and its
 *              exported PADDING/HEADER_HEIGHT — the exact frame chrome a
 *              container band's HEADER_ALLOWANCE reserves room for, so the
 *              two can't drift apart; clearCollisions — Re-layout branch's
 *              own K27-fix-round answer to the same class of bug, a shift
 *              instead of a partition),
 *              frontend/src/App.tsx (layoutMode state and the Lanes button/
 *              palette command that call lanesPositions),
 *              frontend/src/lenses.ts (criticalPath — an independently
 *              written longest-path DP over the same substitution; not
 *              shared with this file on purpose, see needsDepth's comment)
 * @design      PLAN2.md §2.3-2.5
 */
import { HEADER_HEIGHT, PADDING, resolveEndpoint, type Grouping } from "./containers";
import { NODE_HEIGHT, NODE_WIDTH, type LayoutContext } from "./layout";
import type { PlanNode, Position } from "./types";

// Generous relative to elk's own 90px between-layers gap (layout.ts) so a
// lane visibly reads as its own column rather than a tighter Auto.
const COLUMN_SPACING = NODE_WIDTH + 130;
const ROW_SPACING = NODE_HEIGHT + 40;
// The exact top allowance containers.ts's boundingBox reserves above a
// container's topmost member (PADDING above the header strip, then
// HEADER_HEIGHT itself) — imported, not re-guessed, so a container band is
// ALWAYS at least as tall as the frame that will actually be drawn over it.
const HEADER_ALLOWANCE = PADDING + HEADER_HEIGHT;
// Extra clearance between one band and the next, on top of HEADER_ALLOWANCE
// and ROW_SPACING's own slack — belt-and-suspenders visual breathing room,
// not load-bearing for the separation guarantee (bands never overlap either
// way; this only keeps adjacent bands from looking fused together).
const BAND_GAP = 60;
// Sentinel band key for ungrouped leaves and collapsed-container chips — a
// real node id is never the empty string, so this can never collide with an
// actual container id used as a band key.
const UNGROUPED_BAND = "";

export interface LanesResult {
  positions: Record<string, Position>;
  // node id -> its column index (0 = a root, no visible `needs` of its
  // own) — exported alongside positions since x alone doesn't self-announce
  // which column it means; verification (and any future golden test) reads
  // this instead of reverse-dividing x by COLUMN_SPACING.
  columns: Record<string, number>;
}

/** Which node ids are actually on the canvas right now: everything except a
 * member hidden inside a currently-collapsed container — the same
 * visibility rule layout.ts's elk graph and lenses.ts's Flow/Risk apply,
 * kept as a one-line filter here rather than imported: not enough surface
 * to justify a shared export. Used for DEPTH computation (below), which
 * must see every visible id including a container's own — isPositionable
 * (below that) is the separate, narrower filter for which of those actually
 * get a row. */
function visibleIds(nodes: PlanNode[], context: LayoutContext): string[] {
  return nodes
    .map((node) => node.id)
    .filter((id) => {
      const parent = context.assignments.get(id);
      return !(parent && context.collapsed.has(parent));
    });
}

/** Whether `id` needs a row of its own at all: an EXPANDED container's own
 * id doesn't — containers.ts's buildContainerNode always derives its frame
 * from boundingBox over its MEMBERS, ignoring any position stored under the
 * container's own id, so reserving one here would only inflate the
 * ungrouped band's height for a value nothing ever reads. A COLLAPSED
 * container's own id DOES need one (buildContainerNode uses it as-is — no
 * boundingBox call for a chip); an ordinary leaf always does too. */
function isPositionable(id: string, context: LayoutContext): boolean {
  return !(context.containers.has(id) && !context.collapsed.has(id));
}

/**
 * Longest-path depth from a root, over the SUBSTITUTED graph (resolveEndpoint
 * — collapsed containers stand in for their hidden members, exactly like
 * layout.ts's elk graph and lenses.ts's criticalPath/riskLens). A
 * deliberately independent Kahn+DP pass rather than importing lenses.ts's
 * own (unexported) version of this shape: lenses.ts computes ONE best chain
 * for the Flow lens, this needs the FULL per-node distance map, and layout
 * is a more primitive concern than lens emphasis in this codebase's own
 * layering — sharing would point that dependency backwards. A hand-edited
 * file mid-cycle must never hang the browser: a cycle is reported once via
 * console.warn and every node the topological pass never reaches defaults
 * to column 0 rather than looping. Takes the FULL `visible` set (container
 * ids included, even ones isPositionable will later drop) — a container's
 * own depth still has to propagate to whatever transitively needs IT
 * directly, even though the container itself never gets a row.
 */
function needsDepth(nodes: PlanNode[], visible: string[], context: LayoutContext): Map<string, number> {
  const ids = new Set(nodes.map((node) => node.id));
  const forward = new Map<string, Set<string>>();
  const indegree = new Map<string, number>(visible.map((id) => [id, 0]));
  for (const node of nodes) {
    for (const dep of node.needs) {
      if (!ids.has(dep)) continue;
      const from = resolveEndpoint(dep, context.assignments, context.collapsed);
      const to = resolveEndpoint(node.id, context.assignments, context.collapsed);
      if (from === to) continue;
      const targets = forward.get(from);
      if (targets) targets.add(to);
      else forward.set(from, new Set([to]));
    }
  }
  for (const targets of forward.values()) {
    for (const to of targets) indegree.set(to, (indegree.get(to) ?? 0) + 1);
  }

  const depth = new Map<string, number>(visible.map((id) => [id, 0]));
  const queue = visible.filter((id) => (indegree.get(id) ?? 0) === 0).sort();
  let resolved = 0;
  let cursor = 0;
  while (cursor < queue.length) {
    const id = queue[cursor];
    cursor += 1;
    resolved += 1;
    for (const to of [...(forward.get(id) ?? [])].sort()) {
      depth.set(to, Math.max(depth.get(to) ?? 0, (depth.get(id) ?? 0) + 1));
      const next = (indegree.get(to) ?? 0) - 1;
      indegree.set(to, next);
      if (next === 0) queue.push(to);
    }
  }
  if (resolved < visible.length) {
    console.warn("Lanes layout: cycle in the visible graph — unresolved nodes default to column 0");
  }
  return depth;
}

/** Which band `id` belongs to: its container's id when `id` is a visible
 * member (assignments only ever maps a member to its container, and
 * `placed` already excludes a HIDDEN member — so any member reaching this
 * function is, by construction, in a container that currently has at least
 * this one visible member), else the shared UNGROUPED_BAND — ordinary
 * ungrouped leaves and collapsed-container chips alike. */
function bandOf(id: string, assignments: Grouping["assignments"]): string {
  return assignments.get(id) ?? UNGROUPED_BAND;
}

/** Depth-lanes positions for every positionable visible node (PLAN2.md
 * §2.3-2.5, K27 fix round): x by NEEDS-DEPTH as before; y now assigned in
 * per-container BANDS (this file's header) — within one band, columns by
 * depth, rows within a (band, column) cell ordered by id. */
export function lanesPositions(nodes: PlanNode[], context: LayoutContext): LanesResult {
  const visible = visibleIds(nodes, context);
  const depth = needsDepth(nodes, visible, context);
  const placed = visible.filter((id) => isPositionable(id, context));

  const cells = new Map<string, Map<number, string[]>>(); // band -> column -> ids
  for (const id of placed) {
    const band = bandOf(id, context.assignments);
    const col = depth.get(id) ?? 0;
    let byColumn = cells.get(band);
    if (!byColumn) {
      byColumn = new Map();
      cells.set(band, byColumn);
    }
    const list = byColumn.get(col);
    if (list) list.push(id);
    else byColumn.set(col, [id]);
  }

  // Deterministic stacking order: container id ascending, ungrouped last.
  const containerBands = [...cells.keys()].filter((band) => band !== UNGROUPED_BAND).sort();
  const bandOrder = cells.has(UNGROUPED_BAND) ? [...containerBands, UNGROUPED_BAND] : containerBands;

  const positions: Record<string, Position> = {};
  const columns: Record<string, number> = {};
  let y = 0;
  for (const band of bandOrder) {
    const byColumn = cells.get(band);
    if (!byColumn) continue; // unreachable — band keys come from cells itself
    const headerOffset = band === UNGROUPED_BAND ? 0 : HEADER_ALLOWANCE;
    let rows = 0;
    for (const [col, ids] of byColumn) {
      const ordered = [...ids].sort();
      ordered.forEach((id, row) => {
        positions[id] = { x: col * COLUMN_SPACING, y: y + headerOffset + row * ROW_SPACING };
        columns[id] = col;
      });
      rows = Math.max(rows, ordered.length);
    }
    // Band height = its worst column's stack (this file's own documented
    // compactness tradeoff), plus the header allowance already reserved
    // above, plus the inter-band gap before the next one starts.
    y += headerOffset + rows * ROW_SPACING + BAND_GAP;
  }
  return { positions, columns };
}
