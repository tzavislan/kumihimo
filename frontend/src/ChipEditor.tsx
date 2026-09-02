/**
 * @file        frontend/src/ChipEditor.tsx
 * @purpose     One relationship field (needs/agents/skills) as removable
 *              chips plus an id-autocomplete add input (K30). Purely
 *              presentational: `values`/`options`/`titleOf` describe what to
 *              show, `onAdd`/`onRemove` are the caller's own link/unlink
 *              callbacks — this component knows nothing about payloads or
 *              ops envelopes, the same "primitives and callbacks in, JSX
 *              out" shape LensBar.tsx already uses.
 * @layer       frontend
 * @tags        form, chips, autocomplete, ops, mentions
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
}

/** A removable-chip row for one edge field, with a datalist-backed add
 * input: Enter or the Add button commits the typed id, each chip's ×
 * removes it immediately (no staged/Save step — same "gesture is the op"
 * model drawing or removing a canvas edge already uses). */
export function ChipEditor({ fieldKey, label, values, options, titleOf, onAdd, onRemove }: ChipEditorProps) {
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
      <button type="button" aria-label={`Add ${label.toLowerCase()}`} onClick={commit} disabled={!draft.trim()}>
        Add
      </button>
    </div>
  );
}
