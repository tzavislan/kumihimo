/**
 * @file        frontend/src/lenses.ts
 * @purpose     The lens bar's math (PLAN2.md §2.3, §3): pure functions
 *              computing which visual treatment each node/edge gets under
 *              Status, Flow, Risk, or Crew — Structure is the baseline
 *              (today's rendering, zero extra computation). Status's ready
 *              frontier mirrors kumihimo/mcp/tools.py's ready() EXACTLY (same
 *              own-status-must-be-todo rule, same DONE_VALUES, same
 *              dangling-dependency-blocks semantics) so the canvas never
 *              disagrees with the MCP tool. Flow and Risk both walk the needs
 *              graph with collapsed containers substituted for their hidden
 *              members — the same substitution containers.ts's
 *              resolveEndpoint and layout.ts's elk graph already use,
 *              imported rather than re-derived so all three can never drift
 *              apart. Crew (K30) needs no such substitution — its tint is a
 *              node's own `agents`/kind, read directly regardless of whether
 *              it's currently hidden inside a collapsed container — so it
 *              takes the flat node list only. No React, no DOM.
 * @layer       frontend
 * @tags        lenses, status, ready, flow, critical-path, risk, topo-sort,
 *              crew, mentions
 * @related     frontend/src/canvasBuild.ts (calls lensNodeClasses/
 *              flowEdgeClassName/crewEdgeClassName while building the RF
 *              nodes/edges arrays),
 *              frontend/src/App.tsx (lens state, computeLensContext once per
 *              payload/render, gates all of it behind !focus && !trace —
 *              PLAN2.md §2.3's documented "focus/trace suspends lens
 *              emphasis"),
 *              frontend/src/LensBar.tsx (the sidebar segmented control),
 *              frontend/src/containers.ts (resolveEndpoint — the collapsed-
 *              container substitution Flow/Risk both reuse),
 *              frontend/src/cones.ts (descendantsOf — Risk's blast radius is
 *              this same BFS, unioned across every seed then substituted),
 *              frontend/src/edges.ts (kumi-edge-mention-trains — the class
 *              crewEdgeClassName keys its emphasis off of),
 *              frontend/src/useGraphKeyboard.ts (keys 1-5 call onLensChange,
 *              positionally off LENS_ORDER — nothing there names "crew"),
 *              kumihimo/mcp/tools.py (ready() — the rule readyFrontier mirrors
 *              byte-for-byte; read it before touching readyFrontier)
 * @design      PLAN2.md §2.3, §3
 */
import { resolveEndpoint } from "./containers";
import { descendantsOf } from "./cones";
import type { PlanNode } from "./types";

export type Lens = "structure" | "status" | "flow" | "risk" | "crew";

export const LENS_ORDER: Lens[] = ["structure", "status", "flow", "risk", "crew"];

export const LENS_LABELS: Record<Lens, string> = {
  structure: "Structure",
  status: "Status",
  flow: "Flow",
  risk: "Risk",
  crew: "Crew",
};

// ------------------------------------------------------------------------
// Status
// ------------------------------------------------------------------------

// kumihimo/mcp/tools.py's DONE_VALUES, verbatim: a task's "done", a
// decision's "settled", a question's "answered" — the terminal values across
// the engineering pack's status-bearing kinds.
const DONE_VALUES = new Set(["done", "settled", "answered"]);

function statusOf(node: PlanNode | undefined): string | null {
  const value = node?.effective.status;
  return typeof value === "string" ? value : null;
}

/**
 * The ready frontier: nodes whose OWN effective status is exactly "todo" and
 * whose every `needs` target is satisfied (no status field of its own, or an
 * effective status in DONE_VALUES).
 *
 * @purpose  A byte-for-byte port of kumihimo/mcp/tools.py's ready(), over the
 *           payload's already-server-computed `effective` fields rather than
 *           recomputing them — payload.py fills `effective` via the exact
 *           same kinds_module.effective_fields call ready() itself uses, so
 *           the two can never see a different value for the same node.
 *           Deliberately NOT "every EXISTING needs-target is done", the
 *           softer rule the K26 queue text's own prose floated: a DANGLING
 *           needs-target blocks readiness in the MCP tool (satisfied=False
 *           the instant `target is None`, before any status check), so it
 *           blocks it here too. Per the queue text's own instruction, this
 *           function — not that sentence — is the rule; see this file's
 *           header.
 */
export function readyFrontier(nodes: PlanNode[]): Set<string> {
  const byId = new Map(nodes.map((node) => [node.id, node]));
  const ready = new Set<string>();
  for (const node of nodes) {
    if (statusOf(node) !== "todo") continue;
    let satisfied = true;
    for (const dep of node.needs) {
      const target = byId.get(dep);
      if (!target) {
        satisfied = false;
        break;
      }
      const depStatus = statusOf(target);
      if (depStatus !== null && !DONE_VALUES.has(depStatus)) {
        satisfied = false;
        break;
      }
    }
    if (satisfied) ready.add(node.id);
  }
  return ready;
}

export type StatusCategory = "todo" | "doing" | "blocked" | "done";

/**
 * Which of the Status lens's four tokens a node's effective status maps to,
 * or null when nothing should tint it (no status field at all — milestones,
 * risks). "doing"/"blocked" are literal; DONE_VALUES (done/settled/answered)
 * all read as the "done" tinge, and "todo"/"open" both read as neutral
 * "todo". The queue text names only task's four states as tokens; this
 * generalizes them across decision/question by the same done/not-done split
 * ready() already draws, rather than leaving every decision/question
 * permanently untinted under this lens — a documented judgment call, not a
 * server-side rule to mirror.
 */
export function statusCategory(node: PlanNode): StatusCategory | null {
  const status = statusOf(node);
  if (status === null) return null;
  if (status === "doing" || status === "blocked") return status;
  if (DONE_VALUES.has(status)) return "done";
  if (status === "todo" || status === "open") return "todo";
  return null;
}

function statusClassName(node: PlanNode): string | undefined {
  const category = statusCategory(node);
  return category && category !== "todo" ? `kumi-status-${category}` : undefined;
}

/**
 * The ready-glow set as it should actually render: a ready leaf renders
 * itself; a ready node hidden inside a collapsed container substitutes for
 * that container (the same rule fix B applies to cone tinting), so folding a
 * milestone never silently swallows "this is unblocked." readyFrontier
 * itself (the raw, un-substituted set) is what must match the MCP tool
 * exactly — this is the presentation layer on top of it, not a second rule.
 */
export function visibleReadyIds(
  nodes: PlanNode[],
  assignments: Map<string, string>,
  collapsed: Set<string>,
): Set<string> {
  const visible = new Set<string>();
  for (const id of readyFrontier(nodes)) visible.add(resolveEndpoint(id, assignments, collapsed));
  return visible;
}

// ------------------------------------------------------------------------
// Flow
// ------------------------------------------------------------------------

export interface FlowResult {
  nodes: Set<string>;
  // "from->to" visible-id pairs, matching containerEdges' rerouted
  // source/target exactly (both walk through the same resolveEndpoint).
  edges: Set<string>;
}

const EMPTY_FLOW: FlowResult = { nodes: new Set(), edges: new Set() };

/** Visible-id forward adjacency (dependency -> dependent) shared by Flow's
 * critical path and Risk's descendant walk — built once per call so the two
 * lenses can't accidentally see a different substitution. */
function visibleForward(
  nodes: PlanNode[],
  assignments: Map<string, string>,
  collapsed: Set<string>,
): Map<string, Set<string>> {
  const ids = new Set(nodes.map((node) => node.id));
  const forward = new Map<string, Set<string>>();
  for (const node of nodes) {
    for (const dep of node.needs) {
      if (!ids.has(dep)) continue;
      const from = resolveEndpoint(dep, assignments, collapsed);
      const to = resolveEndpoint(node.id, assignments, collapsed);
      if (from === to) continue;
      const targets = forward.get(from);
      if (targets) targets.add(to);
      else forward.set(from, new Set([to]));
    }
  }
  return forward;
}

/**
 * The longest needs-chain through the VISIBLE graph: collapsed containers
 * stand in for their hidden members (containers.ts's resolveEndpoint — the
 * same substitution layout.ts's elk graph uses), self-loops and dangling
 * targets drop out, and multi-edges collapsing onto the same visible pair
 * count once. Longest path by hop count via topological DP; a Kahn pass
 * first proves the visible graph is acyclic — it must be, plans are checked
 * DAGs, but a hand-edited file mid-cycle or a substitution bug must never
 * hang the browser — falling back to no emphasis with one console.warn
 * rather than looping or drawing something wrong.
 */
export function criticalPath(
  nodes: PlanNode[],
  assignments: Map<string, string>,
  collapsed: Set<string>,
): FlowResult {
  const allVisible = new Set(nodes.map((node) => resolveEndpoint(node.id, assignments, collapsed)));
  const forward = visibleForward(nodes, assignments, collapsed);

  // Kahn, sorted seed and sorted expansion so the same plan always yields
  // the same chain (view-state determinism, not a formal invariant, but
  // cheap here and it's what makes the required "print the critical path
  // ids" verification reproducible run to run).
  const indegree = new Map<string, number>();
  for (const id of allVisible) indegree.set(id, 0);
  for (const targets of forward.values()) {
    for (const to of targets) indegree.set(to, (indegree.get(to) ?? 0) + 1);
  }
  const queue = [...allVisible].filter((id) => indegree.get(id) === 0).sort();
  const order: string[] = [];
  let cursor = 0;
  while (cursor < queue.length) {
    const id = queue[cursor];
    cursor += 1;
    order.push(id);
    for (const to of [...(forward.get(id) ?? [])].sort()) {
      const next = (indegree.get(to) ?? 0) - 1;
      indegree.set(to, next);
      if (next === 0) queue.push(to);
    }
  }
  if (order.length < allVisible.size) {
    console.warn("Flow lens: cycle in the visible graph — critical path emphasis disabled");
    return EMPTY_FLOW;
  }

  const distance = new Map<string, number>(order.map((id) => [id, 0]));
  const previous = new Map<string, string | null>(order.map((id) => [id, null]));
  for (const id of order) {
    for (const to of forward.get(id) ?? []) {
      const candidate = (distance.get(id) ?? 0) + 1;
      if (candidate > (distance.get(to) ?? 0)) {
        distance.set(to, candidate);
        previous.set(to, id);
      }
    }
  }

  let end: string | null = null;
  let best = -1;
  for (const id of order) {
    const d = distance.get(id) ?? 0;
    if (d > best) {
      best = d;
      end = id;
    }
  }
  const pathNodes = new Set<string>();
  const pathEdges = new Set<string>();
  let step = end;
  while (step !== null) {
    pathNodes.add(step);
    const before: string | null = previous.get(step) ?? null;
    if (before !== null) pathEdges.add(`${before}->${step}`);
    step = before;
  }
  return { nodes: pathNodes, edges: pathEdges };
}

/** The Flow lens's node class: bold/accented on the critical path, undefined
 * (unchanged) everywhere else — only edges get a "faint" treatment off-path. */
export function flowNodeClassName(id: string, flow: FlowResult): string | undefined {
  return flow.nodes.has(id) ? "kumi-flow-critical" : undefined;
}

/** The Flow lens's edge class: bold on the critical path (needs edges only —
 * `isNeedsEdge` false short-circuits any edge kind the chain never touches),
 * faint everywhere else. */
export function flowEdgeClassName(
  source: string,
  target: string,
  isNeedsEdge: boolean,
  flow: FlowResult,
): string {
  const critical = isNeedsEdge && flow.edges.has(`${source}->${target}`);
  return critical ? "kumi-flow-critical-edge" : "kumi-flow-faint-edge";
}

// ------------------------------------------------------------------------
// Risk
// ------------------------------------------------------------------------

export interface RiskResult {
  sources: Set<string>;
  shadow: Set<string>;
}

const EMPTY_RISK: RiskResult = { sources: new Set(), shadow: new Set() };

/**
 * Risk lens seeds and their blast radius: every `risk`-kind node, plus every
 * `decision`/`question` node whose effective status is "open". The blast
 * radius is each seed's descendant cone (cones.ts's descendantsOf — the same
 * BFS Focus already uses, unioned across every seed by raw id, since a
 * hop-distance from one particular seed means nothing here, only
 * membership), THEN mapped through resolveEndpoint to visible ids — member-
 * substituted like Flow, so a seed or a shadowed node hidden inside a
 * collapsed container makes that container a source or shadow in its place.
 * A node that's both a raw descendant of some seed AND itself a seed stays a
 * source only (riskClassName's own precedence would resolve it the same way
 * regardless, but there's no reason for RiskResult to double-list it).
 */
export function riskLens(
  nodes: PlanNode[],
  assignments: Map<string, string>,
  collapsed: Set<string>,
): RiskResult {
  const rawSources: string[] = [];
  for (const node of nodes) {
    const isOpenDecisionOrQuestion =
      (node.kind === "decision" || node.kind === "question") && statusOf(node) === "open";
    if (node.kind === "risk" || isOpenDecisionOrQuestion) rawSources.push(node.id);
  }
  if (rawSources.length === 0) return EMPTY_RISK;

  const sources = new Set(rawSources.map((id) => resolveEndpoint(id, assignments, collapsed)));
  const shadow = new Set<string>();
  for (const seed of rawSources) {
    for (const id of descendantsOf(nodes, seed).keys()) {
      const visible = resolveEndpoint(id, assignments, collapsed);
      if (!sources.has(visible)) shadow.add(visible);
    }
  }
  return { sources, shadow };
}

/** The Risk lens's per-node class: enlarged presence for a source, a shaded
 * tint for its descendant blast radius, a slight dim for everything else —
 * "everything else" only exists once at least one source does, or there is
 * nothing to contrast it against. */
function riskClassName(id: string, risk: RiskResult): string | undefined {
  if (risk.sources.has(id)) return "kumi-risk-source";
  if (risk.shadow.has(id)) return "kumi-risk-shadow";
  return risk.sources.size > 0 ? "kumi-risk-dim" : undefined;
}

// ------------------------------------------------------------------------
// Crew (K30, PLAN2.md §3)
// ------------------------------------------------------------------------

export interface CrewTint {
  // Resolved CSS color for the Crew lens's node tint (border-left stripe,
  // far-tier chip fill, container frame) — a resolved color string, not a
  // --kumi-* token, by the same "data-derived, not a token" exception
  // KumiNode.tsx's far-tier chip and derive.ts's colorFor already carve
  // out — there's no finite palette to name in CSS when the hue depends on
  // how many agent nodes a given plan happens to have.
  color: string;
  // Readable text color (#ffffff or #000000) for anything rendered directly
  // ON `color` rather than beside it — today just the kind pill's
  // background, which the tokens-only .kumi-pill rule (fixed white) can't
  // answer for an arbitrary runtime hue (fix round: hue ~90-165 at this
  // tint's own saturation/lightness measured under 3:1 against white). Never
  // applied outside a crew-tinted pill — the --kumi-pill-text token itself
  // is untouched for every other node/lens.
  text: string;
}

export interface CrewResult {
  // Node id -> its tint (color + readable text): an agent node's own hue
  // (strong), or its first assigned agent's hue (softer) for anything that
  // mentions one.
  tint: Map<string, CrewTint>;
  // task-kind nodes with an empty `agents` list — unassigned work, the "who
  // does this" gap PLAN2.md §3's crew objects exist to close made visible.
  unassigned: Set<string>;
}

// Golden-angle hue step: spreads any number of agents evenly around the
// wheel (no fixed-size palette to run out of, unlike KIND_COLORS), with
// adjacent sorted indices never landing on visually close hues.
const GOLDEN_ANGLE = 137.508;

/** sRGB (0-255) -> WCAG relative luminance: linearize each channel, then the
 * standard 0.2126/0.7152/0.0722 weighted sum. The one transform both
 * crewTextColor's contrast comparison and the simpler ~0.179 threshold the
 * spec documents are built on. */
function relativeLuminance(r: number, g: number, b: number): number {
  const linear = (channel: number): number => {
    const s = channel / 255;
    return s <= 0.04045 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4);
  };
  return 0.2126 * linear(r) + 0.7152 * linear(g) + 0.0722 * linear(b);
}

/** WCAG contrast ratio between two relative luminances (each 0-1), always
 * >= 1 regardless of argument order. */
function contrastRatio(luminanceA: number, luminanceB: number): number {
  const lighter = Math.max(luminanceA, luminanceB);
  const darker = Math.min(luminanceA, luminanceB);
  return (lighter + 0.05) / (darker + 0.05);
}

/** hsl(h, s, l) -> [r, g, b] in 0-255 — the one conversion crewTextColor
 * needs, since every tint crewLens hands out is built from hue/saturation/
 * lightness numbers, never a hex string, and there's no reason to round-trip
 * through a CSS string just to parse it back apart. Standard six-sector
 * formula; h in degrees, s/l in 0-1. */
function hslToRgb(h: number, s: number, l: number): [number, number, number] {
  const c = (1 - Math.abs(2 * l - 1)) * s;
  const hp = h / 60;
  const x = c * (1 - Math.abs((hp % 2) - 1));
  const [r1, g1, b1] =
    hp < 1 ? [c, x, 0] : hp < 2 ? [x, c, 0] : hp < 3 ? [0, c, x] : hp < 4 ? [0, x, c] : hp < 5 ? [x, 0, c] : [c, 0, x];
  const m = l - c / 2;
  return [Math.round((r1 + m) * 255), Math.round((g1 + m) * 255), Math.round((b1 + m) * 255)];
}

/**
 * The readable text color (#ffffff or #000000) for one hsl(hue, sat%,
 * light%) crew tint: WCAG contrast ratio against both candidates, the
 * higher wins (fix round, critic-caught — hue ~90-165 tints failed white
 * text at 1.9-2.3:1, well under even the 3:1 large-text floor). Exported and
 * pure so it's independently checkable outside a browser: feed it any hue/
 * saturation/lightness triple and get back whichever of the two candidates
 * actually reads, never a third color and never a --kumi-* token — pill
 * text stays var(--kumi-pill-text) everywhere this isn't applied.
 *
 * @purpose  This is the real contrast-ratio comparison, not the cheaper
 *           "background relative luminance > ~0.179 -> black else white"
 *           threshold approximation the same WCAG math also supports; the
 *           two agree almost everywhere; a full ratio comparison is used
 *           here since it's no more code and never needs re-deriving the
 *           crossover constant if the two candidate colors ever change from
 *           pure black/white.
 */
export function crewTextColor(hue: number, saturationPct: number, lightnessPct: number): string {
  const [r, g, b] = hslToRgb(hue, saturationPct / 100, lightnessPct / 100);
  const bgLuminance = relativeLuminance(r, g, b);
  const whiteContrast = contrastRatio(bgLuminance, 1);
  const blackContrast = contrastRatio(bgLuminance, 0);
  return whiteContrast >= blackContrast ? "#ffffff" : "#000000";
}

/** One resolved CrewTint for a given hue at a given saturation/lightness —
 * shared by both the agent-self and mentioned-by branches below so the
 * color and its text never go computed two different ways. */
function crewTint(hue: number, saturationPct: number, lightnessPct: number): CrewTint {
  return {
    color: `hsl(${hue}, ${saturationPct}%, ${lightnessPct}%)`,
    text: crewTextColor(hue, saturationPct, lightnessPct),
  };
}

/**
 * Every node's Crew-lens tint and the unassigned-work set, in one pass.
 * Agent ids are sorted first so the same plan always assigns the same hues
 * run to run (view-state determinism, the same reasoning as Flow's sorted
 * Kahn seed) — the accepted tradeoff is that adding or removing an agent can
 * reshuffle every other agent's hue, since the rule is "sorted ids -> hue
 * rotation" by index, not a hash stable against set changes; the queue text
 * asks for the simple sorted-index scheme, not the hash-stable one.
 */
export function crewLens(nodes: PlanNode[]): CrewResult {
  const agentIds = nodes
    .filter((node) => node.kind === "agent")
    .map((node) => node.id)
    .sort();
  const hueOf = new Map<string, number>(agentIds.map((id, index) => [id, (index * GOLDEN_ANGLE) % 360]));
  const tint = new Map<string, CrewTint>();
  const unassigned = new Set<string>();
  for (const node of nodes) {
    if (node.kind === "agent") {
      // An agent node's own hue, strongly (higher saturation, lower
      // lightness) than the softer tint anything merely mentioning it gets
      // below — the source of a color on the canvas reads as the strongest
      // instance of it.
      const hue = hueOf.get(node.id);
      if (hue !== undefined) tint.set(node.id, crewTint(hue, 70, 45));
      continue;
    }
    if (node.kind === "task" && node.agents.length === 0) unassigned.add(node.id);
    const first = node.agents[0];
    const hue = first !== undefined ? hueOf.get(first) : undefined;
    if (hue !== undefined) tint.set(node.id, crewTint(hue, 55, 60));
  }
  return { tint, unassigned };
}

/** The Crew lens's per-edge class: trains edges (edges.ts's own
 * kumi-edge-mention-trains class) pop, every other kind recedes — the same
 * bold/faint split Flow uses, but by a stateless className check rather than
 * a graph walk, since "is this a trains edge" needs no traversal to answer. */
export function crewEdgeClassName(className: string): string {
  return className.includes("kumi-edge-mention-trains") ? "kumi-crew-trains-edge" : "kumi-crew-faint-edge";
}

// ------------------------------------------------------------------------
// Combined per-node classes (used by canvasBuild.ts)
// ------------------------------------------------------------------------

export interface LensContext {
  lens: Lens;
  readyIds: Set<string> | null;
  flow: FlowResult | null;
  risk: RiskResult | null;
  crew: CrewResult | null;
}

/** readyIds/flow/risk/crew populated only for the currently-active lens, and
 * only while focus/trace aren't suspending lens emphasis (PLAN2.md §2.3) —
 * the other three always stay null, so lensNodeClasses below is a no-op for
 * them without needing to re-check `lens` itself at every call site. */
export function computeLensContext(
  nodes: PlanNode[],
  lens: Lens,
  active: boolean,
  assignments: Map<string, string>,
  collapsed: Set<string>,
): LensContext {
  return {
    lens,
    readyIds: active && lens === "status" ? visibleReadyIds(nodes, assignments, collapsed) : null,
    flow: active && lens === "flow" ? criticalPath(nodes, assignments, collapsed) : null,
    risk: active && lens === "risk" ? riskLens(nodes, assignments, collapsed) : null,
    crew: active && lens === "crew" ? crewLens(nodes) : null,
  };
}

/**
 * Every lens-driven class for one node, box-shadow precedence baked in:
 * `halo` (from derive.ts's haloClassName, already error-beats-warning
 * resolved) always wins over the Status lens's ready-glow when a node
 * carries both, per PLAN2.md §2.3's documented "halo wins visually if both".
 *
 * @purpose  Gated on ctx.readyIds/flow/risk being non-null, never on
 *           `ctx.lens` directly (a real bug K26's own live verification
 *           caught: checking `ctx.lens === "status"` here tinted done/doing/
 *           blocked right through an active focus, since computeLensContext
 *           only nulls readyIds/flow/risk while suspended — `lens` itself
 *           stays set so the lens bar's own active tab still reads
 *           correctly). readyIds/flow/risk null exactly when their lens
 *           isn't the active one OR focus/trace is suspending it, so
 *           checking them instead of `lens` covers both at once.
 *
 *           A fix-round finding sharpened "halo wins" from a visual
 *           preference into a hard exclusion: `opacity`/`filter`-based
 *           dimming (Status's done tinge, Risk's "everything else" dim) sets
 *           those properties on the SAME .kumi-node the halo's box-shadow
 *           lives on, and opacity composites a box-shadow right along with
 *           everything else on the element — a done node with an error halo
 *           rendered NO discernible ring, not a dim one, contradicting the
 *           documented rule outright. The fix is exclusion, not a CSS
 *           layering trick: a haloed node never gets the STATUS tint class
 *           at all (undimmed, full-strength ring, exactly "halo wins"), and
 *           never gets Risk's kumi-risk-dim specifically — but DOES keep
 *           kumi-risk-source/kumi-risk-shadow (border/transform/background,
 *           no opacity — nothing to wash the ring out, and both are
 *           high-value enough to show alongside a halo rather than hide).
 */
export function lensNodeClasses(
  id: string,
  node: PlanNode,
  halo: string | undefined,
  ctx: LensContext,
): string | undefined {
  const parts: string[] = [];
  if (halo) parts.push(halo);
  else if (ctx.readyIds?.has(id)) parts.push("kumi-status-ready");
  if (ctx.readyIds) {
    const status = halo ? undefined : statusClassName(node);
    if (status) parts.push(status);
  } else if (ctx.flow) {
    const critical = flowNodeClassName(id, ctx.flow);
    if (critical) parts.push(critical);
  } else if (ctx.risk) {
    const riskClass = riskClassName(id, ctx.risk);
    if (riskClass && !(halo && riskClass === "kumi-risk-dim")) parts.push(riskClass);
  } else if (ctx.crew) {
    // Outline channel, like flow-critical/focus-self above — never excluded
    // by a halo (only the opacity-based classes need that, per this
    // function's own precedence note).
    if (ctx.crew.unassigned.has(id)) parts.push("kumi-crew-unassigned");
  }
  return parts.length > 0 ? parts.join(" ") : undefined;
}
