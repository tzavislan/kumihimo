/**
 * @file        frontend/src/useUndoTrail.ts
 * @purpose     K32: the session-scoped undo trail. Every op THIS browser tab
 *              applies through App.tsx's applyOp lands here newest-first (one
 *              push() call per postOp response — the response IS the source,
 *              never the live socket or another session's own pushes), capped
 *              at 50. Each entry carries the inverse envelope /api/ops handed
 *              back (kumihimo/server/ops_api.py's OpOutcome) and the node
 *              digest(s) it preconditions on; enabled/reason is re-derived
 *              against the CURRENT payload on every render, so a live payload
 *              echo (another editor, MCP, a hand edit) grays a stale entry the
 *              moment it arrives, naming which node moved. This hook only
 *              holds state and does that enabled/reason math — posting an
 *              inverse is the caller's job, through the SAME applyOp every
 *              other gesture uses, whose own response then pushes a fresh
 *              entry back here: that's what makes undo-of-undo just another
 *              entry rather than a special case.
 * @layer       frontend
 * @tags        undo, hook, ops, digests
 * @related     frontend/src/App.tsx (owns this hook, pushes from applyOp,
 *              hands `entries` to UndoPanel.tsx and useGraphKeyboard.ts),
 *              frontend/src/UndoPanel.tsx (renders `entries`),
 *              frontend/src/useGraphKeyboard.ts (firstEnabled — what Ctrl+Z
 *              fires),
 *              kumihimo/server/ops_api.py (OpOutcome — the inverse/
 *              preconditions/label shape push() consumes)
 * @design      PLAN2.md §2.5 Undo trail, §5 risk 4, queue item K32
 */
import { useCallback, useRef, useState } from "react";
import type { Payload } from "./types";

export interface Precondition {
  id: string;
  digest: string;
}

export interface UndoEntry {
  id: number;
  label: string;
  inverse: Record<string, unknown> | null;
  preconditions: Precondition[];
}

export interface UndoEntryView extends UndoEntry {
  enabled: boolean;
  // Why it's grayed — null exactly when enabled is true.
  reason: string | null;
}

export interface UndoTrail {
  entries: UndoEntryView[];
  push: (inverse: Record<string, unknown> | null, preconditions: Precondition[], label: string) => void;
}

const MAX_TRAIL = 50;
const NOT_UNDOABLE = "not undoable in v0.2 — git is (docs/howto/editor.md#sync-conflicts-and-undo)";

/** The newest entry that's currently postable, or null when every entry is
 * grayed (or there are none) — entries are already newest-first, so this is
 * just the first match. What Ctrl+Z fires. */
export function firstEnabled(entries: UndoEntryView[]): UndoEntryView | null {
  return entries.find((entry) => entry.enabled) ?? null;
}

/** Session-scoped, in-memory only: a reload starts this empty — the durable
 * undo is still git, exactly as before this existed. */
export function useUndoTrail(payload: Payload | null): UndoTrail {
  const [entries, setEntries] = useState<UndoEntry[]>([]);
  const nextId = useRef(0);

  const push = useCallback(
    (inverse: Record<string, unknown> | null, preconditions: Precondition[], label: string) => {
      setEntries((previous) =>
        [{ id: nextId.current++, label, inverse, preconditions }, ...previous].slice(0, MAX_TRAIL),
      );
    },
    [],
  );

  const digestOf = (nodeId: string): string | undefined =>
    payload?.nodes.find((node) => node.id === nodeId)?.digest;

  const views: UndoEntryView[] = entries.map((entry) => {
    if (entry.inverse === null) return { ...entry, enabled: false, reason: NOT_UNDOABLE };
    const stale = entry.preconditions.find((precondition) => digestOf(precondition.id) !== precondition.digest);
    if (stale) return { ...entry, enabled: false, reason: `${stale.id} changed since` };
    return { ...entry, enabled: true, reason: null };
  });

  return { entries: views, push };
}
