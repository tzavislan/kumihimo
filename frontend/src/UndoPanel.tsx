/**
 * @file        frontend/src/UndoPanel.tsx
 * @purpose     The sidebar's undo trail (K32): a collapsible section listing
 *              this session's own applied ops, newest first, each a button —
 *              enabled while its inverse's precondition digests still match
 *              the live payload, grayed with a title naming why the instant
 *              they don't (another editor, MCP, or a hand edit touched the
 *              same node since). Purely presentational, the same "primitives
 *              and callbacks in, JSX out" split as LensBar.tsx/ChipEditor.tsx:
 *              App.tsx owns the trail state (useUndoTrail.ts) and hands down
 *              `entries` plus one `onUndo` callback — clicking an enabled
 *              entry posts its inverse through the exact same op door every
 *              other gesture already uses.
 * @layer       frontend
 * @tags        undo, sidebar, collapsible
 * @related     frontend/src/useUndoTrail.ts (UndoEntryView, the shape this
 *              renders),
 *              frontend/src/App.tsx (mounts this, wires onUndo to applyOp),
 *              frontend/src/styles.css (.kumi-undo-* rules, both themes)
 * @design      PLAN2.md §2.5 Undo trail, §5 risk 4, queue item K32
 */
import type { UndoEntryView } from "./useUndoTrail";

export interface UndoPanelProps {
  entries: UndoEntryView[];
  onUndo: (entry: UndoEntryView) => void;
}

/** Nothing renders until at least one op has been applied this session —
 * same "quiet until there's something to say" rule Toasts.tsx follows. */
export function UndoPanel({ entries, onUndo }: UndoPanelProps) {
  if (entries.length === 0) return null;
  return (
    <details className="kumi-undo" open>
      <summary>Undo ({entries.length})</summary>
      <ul className="kumi-undo-list">
        {entries.map((entry) => (
          <li key={entry.id}>
            <button
              className="kumi-undo-entry"
              disabled={!entry.enabled}
              title={entry.reason ?? "Undo this"}
              onClick={() => onUndo(entry)}
            >
              <span className="kumi-undo-label">{entry.label}</span>
              {entry.reason ? <span className="kumi-undo-reason">{entry.reason}</span> : null}
            </button>
          </li>
        ))}
      </ul>
    </details>
  );
}
