/**
 * @file        frontend/src/useGraphKeyboard.ts
 * @purpose     Graph-directional keyboard (PLAN2.md §2.5): with the palette
 *              closed and focus outside any form field, digits 1-4 switch
 *              the lens bar (K26) regardless of selection; with a node also
 *              selected, Left/Right walk the first needs dependency/
 *              dependent, Up/Down cycle the selection's sibling ring (other
 *              nodes sharing its first `in` group, or other ungrouped
 *              nodes), F focuses, Delete/Backspace confirms and removes. A
 *              single window-level listener, mounted for as long as the
 *              caller renders — not React Flow's own per-node keyboard
 *              handling (App.tsx disables that in favor of this).
 * @layer       frontend
 * @tags        keyboard, navigation, hook, lenses
 * @related     frontend/src/App.tsx (mounts this with its selection/palette/
 *              lens state and jumpTo/focusOn/applyOp callbacks),
 *              frontend/src/cones.ts (ancestorsOf/descendantsOf, what
 *              focusOn's caller builds the focus lens from),
 *              frontend/src/lenses.ts (the Lens type, LENS_ORDER — 1-4 map to
 *              it positionally so this file never hand-lists lens names),
 *              kumihimo/server/ops_api.py (remove_node, the op Delete sends)
 * @design      PLAN2.md §2.5, §2.3
 */
import { useEffect } from "react";
import { LENS_ORDER, type Lens } from "./lenses";
import type { Payload, PlanNode } from "./types";

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
  jumpTo: (nodeId: string) => void;
  focusOn: (id: string) => void;
  applyOp: (envelope: Record<string, unknown>) => Promise<void>;
  onLensChange: (lens: Lens) => void;
}

// "1".."4" -> LENS_ORDER's positional entries, so this file never hand-lists
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
  jumpTo,
  focusOn,
  applyOp,
  onLensChange,
}: UseGraphKeyboardParams): void {
  // Live with the palette closed and focus outside any form field — the tag
  // guard, same as the spec asks for — regardless of selection, since lens
  // switching (below) doesn't need one; the rest of this handler then bails
  // without a selection. Every arrow move also centers, via jumpTo, so
  // keyboard and mouse selection always agree on what "selected" looks like.
  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if (paletteOpen || !payload) return;
      // Leaves browser/OS chords (Ctrl+F, Alt+Left history-back, etc.) alone.
      if (event.ctrlKey || event.metaKey || event.altKey) return;
      const tag = (event.target as HTMLElement | null)?.tagName;
      if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;

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
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [payload, selectedId, paletteOpen, jumpTo, focusOn, applyOp, onLensChange]);
}
