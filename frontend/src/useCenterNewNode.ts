/**
 * @file        frontend/src/useCenterNewNode.ts
 * @purpose     K41.2: center a freshly added node into view once its
 *              position actually exists. `add_node` never writes a
 *              view.yaml entry (kumihimo/core/ops.py) — a brand-new node
 *              always has a layout gap App.tsx's own position effect fills
 *              afterwards (elk asynchronously, or Lanes/view-no-gaps
 *              synchronously; which of the three fires depends on
 *              `layoutMode`), so the id isn't in `positions` yet at the
 *              moment add_node's own op response lands. `request(id)`
 *              remembers the id in a ref — no re-render of its own, just a
 *              note for the effect below, which watches `positions` (for
 *              WHATEVER reason it changed, not just this) and calls `jumpTo`
 *              the instant an entry for that id actually shows up — the
 *              exact same select+setCenter path the palette's node search
 *              and every keyboard jump already share, reused rather than
 *              this file calling `setCenter` a second way. Extracted out of
 *              App.tsx purely to stay clear of CONVENTIONS.md's line cap
 *              (K26's own reason for canvasBuild.ts/containers.ts existing),
 *              same "wire minimally, extract if needed" call as every other
 *              useXxx.ts hook file here.
 * @layer       frontend
 * @tags        hook, positions, center, add-node
 * @related     frontend/src/App.tsx (the Add button's onClick calls
 *              `request()` once add_node's own op resolves; `jumpTo` is
 *              App.tsx's own callback, passed straight through untouched),
 *              kumihimo/core/ops.py (add_node — confirms the layout gap
 *              this hook exists to close)
 * @design      PLAN2.md §2.1, queue item K41
 */
import { useEffect, useRef } from "react";
import type { Position } from "./types";

/**
 * Returns `request`: call it once with a just-added node's id, and this
 * hook fires `jumpTo` on it the moment `positions` actually carries an
 * entry — silently never, if the add itself failed (payload/positions can
 * then never gain that id) or a later `request` call supersedes it first
 * (only the most recent pending id is ever tracked, matching this
 * codebase's existing "one gesture at a time" simplicity bar rather than
 * queuing every add that's ever outrun its own layout).
 */
export function useCenterNewNode(
  positions: Record<string, Position>,
  jumpTo: (id: string) => void,
): (id: string) => void {
  const pending = useRef<string | null>(null);
  useEffect(() => {
    const id = pending.current;
    if (!id || !positions[id]) return;
    pending.current = null;
    jumpTo(id);
  }, [positions, jumpTo]);
  return (id: string) => {
    pending.current = id;
  };
}
