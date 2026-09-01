/**
 * @file        frontend/src/LensBar.tsx
 * @purpose     The sidebar's lens switcher (PLAN2.md §2.3): a four-way
 *              segmented control — Structure (default), Status, Flow, Risk —
 *              sitting right below the sidebar header. Purely presentational;
 *              App.tsx owns the `lens` state itself, and keys 1-4
 *              (useGraphKeyboard.ts) drive the same onChange from the canvas.
 * @layer       frontend
 * @tags        lenses, sidebar, segmented-control
 * @related     frontend/src/App.tsx (owns lens state, mounts this),
 *              frontend/src/lenses.ts (LENS_ORDER/LENS_LABELS, the Lens type),
 *              frontend/src/useGraphKeyboard.ts (keys 1-4, same onChange),
 *              frontend/src/styles.css (.kumi-lens-* rules)
 * @design      PLAN2.md §2.3
 */
import { LENS_ORDER, LENS_LABELS, type Lens } from "./lenses";

export interface LensBarProps {
  lens: Lens;
  onChange: (lens: Lens) => void;
}

/** Structure/Status/Flow/Risk, one click (or keys 1-4) apart. */
export function LensBar({ lens, onChange }: LensBarProps) {
  return (
    <div className="kumi-lens-bar" role="tablist" aria-label="Lens">
      {LENS_ORDER.map((candidate, index) => (
        <button
          key={candidate}
          role="tab"
          aria-selected={lens === candidate}
          className={`kumi-lens-btn${lens === candidate ? " kumi-lens-active" : ""}`}
          title={`${LENS_LABELS[candidate]} (${index + 1})`}
          onClick={() => onChange(candidate)}
        >
          {LENS_LABELS[candidate]}
        </button>
      ))}
    </div>
  );
}
