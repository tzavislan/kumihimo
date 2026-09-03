/**
 * @file        frontend/src/ChipEditor.tsx
 * @purpose     One relationship field (needs/agents/skills) as removable
 *              chips plus an id-autocomplete add input (K30). Purely
 *              presentational: `values`/`options`/`titleOf` describe what to
 *              show, `onAdd`/`onRemove` are the caller's own link/unlink
 *              callbacks — this component knows nothing about payloads or
 *              ops envelopes, the same "primitives and callbacks in, JSX
 *              out" shape LensBar.tsx already uses. `disabled` (K40) is also
 *              the caller's own call: this component just applies it to the
 *              add input, every chip's ×, and the Add button — NodeForm.tsx
 *              is the one deciding WHEN, off its own in-flight op state.
 * @layer       frontend
 * @tags        form, chips, autocomplete, ops, mentions, race
 * @related     frontend/src/NodeForm.tsx (the sole caller — one instance per
 *              field, building `options`/`titleOf` from its own `nodes` prop
 *              and turning onAdd/onRemove into link/unlink op envelopes),
 *              frontend/src/styles.css (.kumi-chip-* rules),
 *              kumihimo/server/ops_api.py (the link/unlink envelopes those
 *              callbacks post)
 * @design      PLAN2.md §3.2, §3
 */
import { useState } from "react";

export interface ChipOption {
  id: string;
  title: string;
}

export interface ChipEditorProps {
  // Distinguishes this field's <datalist> id when several editors render at
  // once (NodeForm.tsx mounts three) — not shown, just needs to be unique.
  fieldKey: string;
  label: string;
  values: string[];
  // Candidate ids for the add input's autocomplete, already filtered by the
  // caller (kind, self-exclusion, values already present) — this component
  // does no filtering of its own, it only renders what it's given.
  options: ChipOption[];
  titleOf: (id: string) => string;
  onAdd: (id: string) => void;
  onRemove: (id: string) => void;
  // K40: true while NodeForm.tsx has a link/unlink op in flight for THIS
  // node — one shared flag across all three of its ChipEditor rows (not a
  // per-row one), since base_digest is the whole node file's digest, not
  // per-field: a needs-add and an agents-add fired back to back race the
  // exact same stale digest just as much as two needs-adds would. Disables
  // the add input and every chip's × for the round trip, re-enabled only
  // once the op's response — success or failure alike — comes back, which
  // is what actually kills the race the audit found (two fast adds, the
  // second still holding the pre-echo digest, 409ing).
  disabled: boolean;
}

/** A removable-chip row for one edge field, with a datalist-backed add
 * input: Enter or the Add button commits the typed id, each chip's ×
 * removes it immediately (no staged/Save step — same "gesture is the op"
 * model drawing or removing a canvas edge already uses). */
export function ChipEditor({
  fieldKey,
  label,
  values,
  options,
  titleOf,
  onAdd,
  onRemove,
  disabled,
}: ChipEditorProps) {
  const [draft, setDraft] = useState("");
  const listId = `kumi-chip-options-${fieldKey}`;

  const commit = () => {
    const value = draft.trim();
    if (!value) return;
    onAdd(value);
    setDraft("");
  };

  return (
    <div className="kumi-chip-field">
      <label>{label}</label>
      <div className="kumi-chip-list">
        {values.map((id) => (
          <span className="kumi-chip-pill" key={id}>
            {titleOf(id)}
            <button
              type="button"
              className="kumi-chip-remove"
              aria-label={`Remove ${titleOf(id)}`}
              disabled={disabled}
              onClick={() => onRemove(id)}
            >
              ×
            </button>
          </span>
        ))}
        <input
          value={draft}
          list={listId}
          placeholder={`add ${label.toLowerCase()}…`}
          aria-label={`Add ${label.toLowerCase()}`}
          disabled={disabled}
          onChange={(event) => setDraft(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter") {
              event.preventDefault();
              commit();
            }
          }}
        />
      </div>
      <datalist id={listId}>
        {options.map((option) => (
          <option key={option.id} value={option.id}>
            {option.title}
          </option>
        ))}
      </datalist>
      {/* Distinct accessible name from the sidebar's own "Add" (node) button
       * — same visible text is fine (each field's own label above already
       * gives it context), but the two must not share an accessible name:
       * a live regression on the editor-smoke Playwright test caught
       * get_by_role("button", name="Add", exact=True) resolving to all four
       * once a node was selected and every ChipEditor mounted alongside it. */}
      <button
        type="button"
        aria-label={`Add ${label.toLowerCase()}`}
        onClick={commit}
        disabled={disabled || !draft.trim()}
      >
        Add
      </button>
    </div>
  );
}
