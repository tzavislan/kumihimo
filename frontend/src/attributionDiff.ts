/**
 * @file        frontend/src/attributionDiff.ts
 * @purpose     Pure classification for K31 attribution: diff two payloads'
 *              node digests into added/removed/updated, match the newly
 *              shipped `events` (kumihimo/core/ops.py's advisory log, ridden
 *              onto the payload by kumihimo/server/watch.py) against that
 *              diff — targets ∩ changed, first event to claim an id wins,
 *              actor "editor" claims silently — and produce toast text plus
 *              the resolved pulse-target id set. No React, no DOM;
 *              useAttribution.ts is the only caller.
 * @layer       frontend
 * @tags        attribution, events, toasts, pulse, diff
 * @related     frontend/src/useAttribution.ts (the hook wrapping this in
 *              React state, owns the live-payload effect),
 *              frontend/src/containers.ts (resolveEndpoint — a hidden
 *              member's pulse substitutes onto its collapsed container, the
 *              same rule Flow/Risk/Lanes already share),
 *              frontend/src/types.ts (Payload.events, EventLogEntry),
 *              kumihimo/server/watch.py (writes `events` onto the payload
 *              this reads), kumihimo/core/ops.py (actor/op/targets — the
 *              shape of one event)
 * @design      PLAN2.md §2.5 Motion & attribution, queue item K31
 */
import { groupNodes, resolveEndpoint } from "./containers";
import type { EventLogEntry, Payload, PlanNode } from "./types";

type Verb = "added" | "removed" | "updated";

const ACTOR_PREFIX: Record<string, string> = {
  cli: "via CLI",
  mcp: "via MCP",
  api: "via API",
};
const MAX_NAMES = 3;

/** id -> added/removed/updated between two node lists, by digest — the
 * whole classification is this one comparison, no op-specific knowledge. */
function digestDiff(previous: PlanNode[], incoming: PlanNode[]): Map<string, Verb> {
  const before = new Map(previous.map((node) => [node.id, node.digest]));
  const after = new Map(incoming.map((node) => [node.id, node.digest]));
  const changed = new Map<string, Verb>();
  for (const [id, digest] of after) {
    if (!before.has(id)) changed.set(id, "added");
    else if (before.get(id) !== digest) changed.set(id, "updated");
  }
  for (const id of before.keys()) {
    if (!after.has(id)) changed.set(id, "removed");
  }
  return changed;
}

/** A changed id's display name: its title in whichever payload still has
 * it (incoming for added/updated, previous for removed), else the raw id. */
function titleFor(id: string, incoming: Payload, previous: Payload): string {
  const found =
    incoming.nodes.find((node) => node.id === id) ?? previous.nodes.find((node) => node.id === id);
  return found?.title || id;
}

/** One group's toast text: up to 3 (distinct) titles then "+n more", one
 * verb — the shared one, or "changed" when the group mixes added/removed/
 * updated (a rename's old-removed/new-added/referrers-updated, say).
 * Deduped by title BEFORE the 3-name slice and BEFORE counting "+n more":
 * a rename's old and new ids are two different ids with the identical
 * title (renaming touches the filename/id, never the `title:` field), and
 * without this a fix-round bug showed it twice ("Core Service, Core
 * Service, ... updated") instead of once. */
function toastText(
  prefix: string,
  ids: string[],
  verbs: Map<string, Verb>,
  incoming: Payload,
  previous: Payload,
): string {
  const distinctVerbs = new Set(ids.map((id) => verbs.get(id)));
  const verb = distinctVerbs.size === 1 ? [...distinctVerbs][0] : "changed";
  const uniqueTitles = [...new Set(ids.map((id) => titleFor(id, incoming, previous)))];
  const names = uniqueTitles.slice(0, MAX_NAMES);
  const rest = uniqueTitles.length - names.length;
  const label = rest > 0 ? `${names.join(", ")} +${rest} more` : names.join(", ");
  return `${prefix}: ${label} ${verb}`;
}

/** Pulse targets for one claimed group: a hidden member substitutes onto its
 * collapsed container (containers.ts's resolveEndpoint — the same rule
 * Flow/Risk/Lanes already share) so the change is visible somewhere; a
 * removed id has nothing left on the canvas to animate, so it's named in the
 * toast but never pulses. */
function pulseTargets(ids: string[], verbs: Map<string, Verb>, incoming: Payload): Set<string> {
  const grouping = groupNodes(incoming.nodes);
  const collapsed = new Set(incoming.collapsed);
  const targets = new Set<string>();
  for (const id of ids) {
    if (verbs.get(id) === "removed") continue;
    targets.add(resolveEndpoint(id, grouping.assignments, collapsed));
  }
  return targets;
}

export interface AttributionResult {
  toastTexts: string[];
  pulseIds: Set<string>;
}

const EMPTY: AttributionResult = { toastTexts: [], pulseIds: new Set() };

/**
 * The whole K31 pipeline for one live-socket payload: diff against the
 * payload before it, then match `incoming.events` against the diff in file
 * order — first event to claim an id wins, actor "editor" claims its
 * targets silently (the op's own response already updated the UI, no
 * toast, no pulse). Whatever no event explains is "outside edit", still
 * toasted and pulsed — some other tool touched the file. `previous` null
 * (the live socket's own first message, nothing to diff against yet) always
 * yields neither, so opening the editor never toasts its own starting state.
 */
export function diffLivePayload(previous: Payload | null, incoming: Payload): AttributionResult {
  if (!previous) return EMPTY;
  const changed = digestDiff(previous.nodes, incoming.nodes);
  if (changed.size === 0) return EMPTY;
  const unclaimed = new Set(changed.keys());
  const toastTexts: string[] = [];
  const pulseIds = new Set<string>();
  for (const event of incoming.events ?? ([] as EventLogEntry[])) {
    const claim = event.targets.filter((id) => unclaimed.has(id));
    if (claim.length === 0) continue;
    for (const id of claim) unclaimed.delete(id);
    if (event.actor === "editor") continue; // the op response already updated the UI
    const prefix = ACTOR_PREFIX[event.actor] ?? "via API";
    toastTexts.push(toastText(prefix, claim, changed, incoming, previous));
    for (const id of pulseTargets(claim, changed, incoming)) pulseIds.add(id);
  }
  if (unclaimed.size > 0) {
    const rest = [...unclaimed];
    toastTexts.push(toastText("outside edit", rest, changed, incoming, previous));
    for (const id of pulseTargets(rest, changed, incoming)) pulseIds.add(id);
  }
  return { toastTexts, pulseIds };
}
