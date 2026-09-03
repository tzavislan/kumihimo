/**
 * @file        frontend/src/useGraphKeyboard.ts
 * @purpose     Graph-directional keyboard (PLAN2.md §2.5): with the palette
 *              and braid modal both closed and focus outside any form
 *              field, digits 1-5 switch the lens bar (K26; 5 is Crew, K30)
 *              regardless of selection; with a node also
 *              selected, Left/Right walk the first needs dependency/
 *              dependent, Up/Down cycle the selection's sibling ring (other
 *              nodes sharing its first `in` group, or other ungrouped
 *              nodes), F focuses, Delete/Backspace confirms and removes,
 *              and Escape clears the selection (K41.4). Ctrl+Z/Cmd+Z (K32)
 *              fires the undo trail's topmost enabled
 *              entry, regardless of selection — checked ahead of the "leave
 *              ctrl/meta/alt chords alone" bail below, since it IS one, but
 *              behind the same form-field guard every other binding here
 *              already gets. A single window-level listener, mounted for as
 *              long as the caller renders — not React Flow's own per-node
 *              keyboard handling (App.tsx disables that in favor of this).
 *
 *              Escape's own priority chain (K41.4, spans two listeners):
 *              App.tsx keeps its own separate, form-field-agnostic Escape
 *              listener that exits focus/trace first (unchanged by K41.4;
 *              it must keep working even mid-edit in a form field, unlike
 *              everything else here) — while EITHER is active, this hook's
 *              own Escape branch below stays a no-op (`focusOrTraceActive`),
 *              so a press that closes focus/trace never also clears the
 *              selection in the same keystroke. Only once neither is
 *              active does Escape here clear the selection — and, like
 *              every other selection-touching key in this hook, only
 *              outside a form field and outside the palette/modal. So:
 *              first Escape exits focus or trace (selection untouched),
 *              a second Escape (nothing else active) clears the selection —
 *              peeling one layer per press, closest-thing-first.
 * @layer       frontend
 * @tags        keyboard, navigation, hook, lenses, undo, escape
 * @related     frontend/src/App.tsx (mounts this with its selection/palette/
 *              modal/focus/trace/lens/undo-trail state and
 *              jumpTo/focusOn/clearSelection/applyOp callbacks — also owns
 *              the separate Escape listener that exits focus/trace, see
 *              this file's own Escape note above),
 *              frontend/src/cones.ts (ancestorsOf/descendantsOf, what
 *              focusOn's caller builds the focus lens from),
 *              frontend/src/lenses.ts (the Lens type, LENS_ORDER — 1-4 map to
 *              it positionally so this file never hand-lists lens names),
 *              frontend/src/useUndoTrail.ts (firstEnabled, UndoEntryView —
 *              what Ctrl+Z fires),
 *              kumihimo/server/ops_api.py (remove_node, the op Delete sends;
 *              also every op's own inverse, what Ctrl+Z posts)
 * @design      PLAN2.md §2.5, §2.3, queue item K32
 */
import { useEffect } from "react";
import { LENS_ORDER, type Lens } from "./lenses";
import type { Payload, PlanNode } from "./types";
import { firstEnabled, type UndoEntryView } from "./useUndoTrail";

// "First" dependency/dependent is needs[0] / the first node in payload
// order whose needs include this id — simple and deterministic rather than
// tracking a per-selection cursor through a multi-dependency fan-out, which
// the spec explicitly asked to skip in favor of the honest simple version.
function firstDependency(nodes: PlanNode[], id: string): string | null {
  const node = nodes.find((candidate) => candidate.id === id);
  if (!node || node.needs.length === 0) return null;
  const target = node.needs[0];
  return nodes.some((candidate) => candidate.id === target) ? target : null;
}

function firstDependent(nodes: PlanNode[], id: string): string | null {
  return nodes.find((candidate) => candidate.needs.includes(id))?.id ?? null;
}

// Siblings: other nodes sharing this selection's first `in` group, or, when
// the selection belongs to no group, other likewise-ungrouped nodes — both
// rings sorted by id so repeated Up/Down presses cycle a stable order.
function siblingRing(nodes: PlanNode[], id: string): string[] {
  const self = nodes.find((candidate) => candidate.id === id);
  if (!self) return [];
  const group = self.in[0];
  const pool = group
    ? nodes.filter((candidate) => candidate.in.includes(group))
    : nodes.filter((candidate) => candidate.in.length === 0);
  return pool.map((candidate) => candidate.id).sort();
}

function cycleSibling(nodes: PlanNode[], id: string, delta: 1 | -1): string | null {
  const ring = siblingRing(nodes, id);
  if (ring.length <= 1) return null;
  const index = ring.indexOf(id);
  if (index === -1) return null;
  return ring[(index + delta + ring.length) % ring.length];
}

export interface UseGraphKeyboardParams {
  payload: Payload | null;
  selectedId: string | null;
  paletteOpen: boolean;
  // K41.4: the braid preview modal — every binding here stays suspended
  // while it's open (the canvas is fully obscured), reusing the same
  // top-of-handler bail paletteOpen already gets rather than a narrower
  // check on Escape alone.
  modalOpen: boolean;
  // K41.4: true while focus or trace is active (App.tsx's own state,
  // untouched by this hook) — see this file's header for the priority
  // chain this gates Escape's selection-clearing branch behind.
  focusOrTraceActive: boolean;
  jumpTo: (nodeId: string) => void;
  focusOn: (id: string) => void;
  // K41.4: Escape's own second layer, once neither focus nor trace claims
  // the keystroke first — App.tsx's `() => setSelectedId(null)`.
  clearSelection: () => void;
  applyOp: (envelope: Record<string, unknown>) => Promise<void>;
  onLensChange: (lens: Lens) => void;
  // K32: newest-first, enabled/reason already resolved against the live
  // payload — see useUndoTrail.ts. Ctrl+Z fires firstEnabled(undoEntries).
  undoEntries: UndoEntryView[];
}

// "1".."5" -> LENS_ORDER's positional entries, so this file never hand-lists
// lens names and can't drift from lenses.ts/LensBar.tsx's own ordering.
const LENS_KEYS: Record<string, Lens> = Object.fromEntries(
  LENS_ORDER.map((lens, index) => [String(index + 1), lens]),
);

/** Mount the graph-directional keyboard listener; see the file header for
 * the key bindings. */
export function useGraphKeyboard({
  payload,
  selectedId,
  paletteOpen,
  modalOpen,
  focusOrTraceActive,
  jumpTo,
  focusOn,
  clearSelection,
  applyOp,
  onLensChange,
  undoEntries,
}: UseGraphKeyboardParams): void {
  // Live with the palette and braid modal both closed and focus outside any
  // form field — the tag guard, same as the spec asks for — regardless of
  // selection, since lens switching (below) doesn't need one; the rest of
  // this handler then bails without a selection. Every arrow move also
  // centers, via jumpTo, so keyboard and mouse selection always agree on
  // what "selected" looks like.
  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if (paletteOpen || modalOpen || !payload) return;
      const tag = (event.target as HTMLElement | null)?.tagName;
      const inFormField = tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT";

      // Ctrl+Z / Cmd+Z (K32): an intentional ctrl chord, so it's handled
      // ahead of the "leave browser/OS chords alone" bail just below rather
      // than by it — same form-field guard as everything else here, just
      // reached first. Shift+Ctrl+Z (a common redo chord elsewhere) is left
      // alone on purpose: there is no redo here, only more undo entries.
      if (!inFormField && (event.ctrlKey || event.metaKey) && !event.shiftKey && event.key.toLowerCase() === "z") {
        const top = firstEnabled(undoEntries);
        if (top && top.inverse) {
          event.preventDefault();
          void applyOp(top.inverse);
        }
        return;
      }
      // Leaves browser/OS chords (Ctrl+F, Alt+Left history-back, etc.) alone.
      if (event.ctrlKey || event.metaKey || event.altKey) return;
      if (inFormField) return;

      const lens = LENS_KEYS[event.key];
      if (lens) {
        event.preventDefault();
        onLensChange(lens);
        return;
      }
      if (!selectedId) return;

      if (event.key === "ArrowLeft") {
        const target = firstDependency(payload.nodes, selectedId);
        if (target) {
          event.preventDefault();
          jumpTo(target);
        }
      } else if (event.key === "ArrowRight") {
        const target = firstDependent(payload.nodes, selectedId);
        if (target) {
          event.preventDefault();
          jumpTo(target);
        }
      } else if (event.key === "ArrowUp") {
        const target = cycleSibling(payload.nodes, selectedId, -1);
        if (target) {
          event.preventDefault();
          jumpTo(target);
        }
      } else if (event.key === "ArrowDown") {
        const target = cycleSibling(payload.nodes, selectedId, 1);
        if (target) {
          event.preventDefault();
          jumpTo(target);
        }
      } else if (event.key.toLowerCase() === "f") {
        event.preventDefault();
        focusOn(selectedId);
      } else if (event.key === "Delete" || event.key === "Backspace") {
        event.preventDefault();
        const node = payload.nodes.find((candidate) => candidate.id === selectedId);
        if (!node) return;
        // No auto-force: a referenced node's remove_node 400s with the
        // referrer list, and applyOp's existing else-branch already surfaces
        // that in the same notice banner every other op error uses.
        if (window.confirm(`Delete "${node.title || node.id}"?`)) {
          void applyOp({ op: "remove_node", node_id: node.id, base_digest: node.digest });
        }
      } else if (event.key === "Escape" && !focusOrTraceActive) {
        // K41.4: reached only once App.tsx's own Escape listener had
        // nothing to exit this same press — see this file's header.
        event.preventDefault();
        clearSelection();
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [
    payload,
    selectedId,
    paletteOpen,
    modalOpen,
    focusOrTraceActive,
    jumpTo,
    focusOn,
    clearSelection,
    applyOp,
    onLensChange,
    undoEntries,
  ]);
}
