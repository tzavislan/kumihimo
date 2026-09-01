/**
 * @file        frontend/src/derive.ts
 * @purpose     Pure functions turning one payload (or one payload plus an
 *              active lens) into the small per-node facts App.tsx and
 *              KumiNode need to render: node title/color lookups, milestone
 *              member counts, the acceptance checklist, the focus/trace
 *              lens's per-node wrapper class (built on cones.ts's BFS
 *              distances), findings halos and their wrapper class, and the
 *              minimap's fill color. No React, no DOM.
 * @layer       frontend
 * @tags        payload, focus, trace, findings, semantic-zoom, minimap
 * @related     frontend/src/canvasBuild.ts (the nodes/edges builders call
 *              every export here once per payload/render; also the only
 *              other file that reads FocusState.members),
 *              frontend/src/App.tsx (holds FocusState/TraceState as its own
 *              lens state; focusOn builds a container's FocusState.members
 *              from containers.ts's membersByContainer),
 *              frontend/src/cones.ts (the BFS distances coneClassName tints
 *              by, and the ancestor/descendant maps FocusState holds;
 *              containerCones — the source of a container FocusState's own
 *              ancestors/descendants),
 *              frontend/src/KumiNode.tsx (KIND_COLORS/FALLBACK_COLOR colorFor
 *              falls back to; KumiNodeData minimapNodeColor reads),
 *              frontend/src/edges.ts (imports nodeTitle for edgeSentence)
 * @design      PLAN2.md §2.1-2.2, Inherited fixes B and C (K26)
 */
import type { Node } from "@xyflow/react";
import { FALLBACK_COLOR, KIND_COLORS } from "./KumiNode";
import type { Finding, Payload, PlanNode } from "./types";

// Focus and trace are alternatives, never both: entering one clears the
// other so a node's class is never ambiguous between two active lenses.
// Kept here, not App.tsx, since coneClassName below is their only reader.
export interface FocusState {
  id: string;
  ancestors: Map<string, number>;
  descendants: Map<string, number>;
  // Populated only when `id` is itself a container (Inherited fix C, K26):
  // its own members render at full strength, same as the focus node itself,
  // rather than falling through to coneClassName's "unrelated -> dimmed"
  // branch just because cones.ts's containerCones deliberately excludes a
  // container's own members from both its ancestor and descendant cones.
  members?: Set<string>;
}
export interface TraceState {
  a: string;
  b: string;
  nodes: Set<string>;
}

// Bucket BFS distance into the 3 CSS steps (kumi-cone-{up,down}-1..3) the
// tokens fade across; distance 3+ shares the faintest step rather than
// growing an unbounded class list.
function coneStep(distance: number): number {
  return Math.min(distance, 3);
}

/**
 * The node wrapper class for the active lens, or undefined outside one —
 * cone tint for ancestors/descendants, a distinct ring for the focus node
 * itself or a trace endpoint/path node, ~15% dim for everything else.
 *
 * @purpose  `hiddenMembers` is Inherited fix B (K26): pass a collapsed
 *           container's (now-hidden) member ids and its chip is checked
 *           right alongside its own id — closest match wins the same way a
 *           single node's own distance would — so folding a container never
 *           silently drops a member out of the visible cone/trace set. Leaf
 *           nodes call this with no third argument and see identical
 *           behavior to before K26.
 */
export function coneClassName(
  id: string,
  focus: FocusState | null,
  trace: TraceState | null,
  hiddenMembers?: string[],
): string | undefined {
  const candidates = hiddenMembers && hiddenMembers.length > 0 ? [id, ...hiddenMembers] : [id];
  if (focus) {
    if (candidates.some((candidate) => candidate === focus.id || focus.members?.has(candidate))) {
      return "kumi-focus-self";
    }
    const bestUp = closest(candidates, focus.ancestors);
    if (bestUp !== undefined) return `kumi-cone-up-${coneStep(bestUp)}`;
    const bestDown = closest(candidates, focus.descendants);
    if (bestDown !== undefined) return `kumi-cone-down-${coneStep(bestDown)}`;
    return "kumi-dimmed";
  }
  if (trace) {
    return candidates.some((candidate) => trace.nodes.has(candidate)) ? "kumi-trace-node" : "kumi-dimmed";
  }
  return undefined;
}

/** The smallest distance any candidate has in `distances`, or undefined when
 * none of them are in it — shared by coneClassName's up/down checks above. */
function closest(candidates: string[], distances: Map<string, number>): number | undefined {
  let best: number | undefined;
  for (const candidate of candidates) {
    const distance = distances.get(candidate);
    if (distance !== undefined && (best === undefined || distance < best)) best = distance;
  }
  return best;
}

// Milestone member count (PLAN2.md §2.2 mid tier): how many payload nodes
// name this id in their `in` — i.e. how many threads belong to it. One pass
// over every node's `in` list per payload, alongside the nodes-rebuild
// effect that already walks payload.nodes once per render; KumiNode only
// ever sees one node, so this has to happen up here.
export function memberCounts(nodes: PlanNode[]): Map<string, number> {
  const counts = new Map<string, number>();
  for (const node of nodes) {
    for (const group of node.in) {
      counts.set(group, (counts.get(group) ?? 0) + 1);
    }
  }
  return counts;
}

// Near-tier acceptance checklist (PLAN2.md §2.2): only effective.acceptance
// that actually resolved to a list (kinds.yaml's "list" field type) renders
// as checkboxes — a hand-edited file that turned it into a string or number
// must not be coerced into one, so KumiNode gets null instead.
export function acceptanceList(node: PlanNode): string[] | null {
  const value = node.effective.acceptance;
  if (!Array.isArray(value)) return null;
  return value.filter((item): item is string => typeof item === "string");
}

/** A node's kind color: plan-level override, else KumiNode's static
 * per-kind palette, else the neutral fallback. */
export function colorFor(payload: Payload, node: PlanNode): string {
  return payload.kinds[node.kind]?.color ?? KIND_COLORS[node.kind] ?? FALLBACK_COLOR;
}

/** A node's title, or its id when the node is absent from this payload (a
 * dangling edge endpoint mid-edit). */
export function nodeTitle(payload: Payload, id: string): string {
  return payload.nodes.find((node) => node.id === id)?.title ?? id;
}

// Findings-on-the-graph halo (PLAN2.md §2.1): node id -> worst level of any
// finding naming it. finding.where is a node id when the finding is about
// that node; a file-level finding (kumihimo.yaml, a kind's schema) never
// matches an id and so never halos. Error beats warning when a node carries
// both, regardless of which finding came first in payload.findings, since a
// node shows at most one ring. The sidebar's click-to-jump reuses this same
// map's key set as its "is this finding's `where` a node id" check — every
// finding that matches gets inserted here independent of level.
export function findingHalos(nodes: PlanNode[], findings: Finding[]): Map<string, "error" | "warning"> {
  const ids = new Set(nodes.map((node) => node.id));
  const halos = new Map<string, "error" | "warning">();
  for (const finding of findings) {
    if (!ids.has(finding.where)) continue;
    if (finding.level === "error" || !halos.has(finding.where)) {
      halos.set(finding.where, finding.level);
    }
  }
  return halos;
}

// The halo wrapper class for one node, or undefined when it has none —
// composed alongside coneClassName's lens class rather than replacing it,
// same pattern as App.tsx's edges useMemo composing an edge's kind class
// with kumi-edge-dim.
export function haloClassName(id: string, halos: Map<string, "error" | "warning">): string | undefined {
  const level = halos.get(id);
  return level ? `kumi-halo-${level}` : undefined;
}

// MiniMap paints to a <canvas>, not the DOM, so it can't resolve a
// var(--kumi-*) token or read our .kumi-dimmed CSS rule — it wants a color
// string back from this callback. The alpha-hex fallback below is a
// deliberate, narrow exception to the tokens-only rule, not an oversight:
// there is no token to hand it. Cast to the minimal shape rather than
// KumiNodeData specifically — a container node's data (KumiGroupNodeData)
// carries `color` too, and the minimap doesn't care which node type it is.
export function minimapNodeColor(node: Node): string {
  const dimmed = typeof node.className === "string" && node.className.includes("kumi-dimmed");
  if (dimmed) return "#94a3b833";
  return (node.data as { color: string }).color;
}
