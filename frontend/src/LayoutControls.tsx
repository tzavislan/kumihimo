/**
 * @file        frontend/src/LayoutControls.tsx
 * @purpose     The sidebar's layout controls (PLAN2.md §2.3-2.5, K27): the
 *              Auto-layout/Use view.yaml toggle (unchanged), the new Lanes
 *              button next to it, and Re-layout branch on its own row.
 *              Purely presentational, same split as LensBar.tsx — App.tsx
 *              owns layoutMode/selection state and hands down callbacks.
 * @layer       frontend
 * @tags        layout, lanes, sidebar, buttons
 * @related     frontend/src/App.tsx (owns layoutMode state and
 *              relayoutBranch, mounts this),
 *              frontend/src/layout.ts (the LayoutMode type this renders,
 *              and elkBranchPositions — what Re-layout branch runs),
 *              frontend/src/lanes.ts (what the Lanes button runs)
 * @design      PLAN2.md §2.3-2.5
 */
import type { LayoutMode } from "./layout";

export interface LayoutControlsProps {
  mode: LayoutMode;
  onToggleAuto: () => void;
  onLanes: () => void;
  onRelayoutBranch: () => void;
  // Re-layout branch needs a selection to have any scope at all; disabled
  // rather than silently no-op-ing, same convention as the Add button's
  // disabled={!newNode.id} elsewhere in the sidebar.
  canRelayout: boolean;
}

/** Auto-layout/Use view.yaml, Lanes, and Re-layout branch — see the file
 * header for why these three live together, apart from Braid (App.tsx keeps
 * that one, unchanged). */
export function LayoutControls({ mode, onToggleAuto, onLanes, onRelayoutBranch, canRelayout }: LayoutControlsProps) {
  return (
    <>
      <div className="kumi-actions">
        <button onClick={onToggleAuto}>{mode === "view" ? "Auto-layout" : "Use view.yaml"}</button>
        <button onClick={onLanes}>{mode === "lanes" ? "Lanes (on)" : "Lanes"}</button>
      </div>
      <div className="kumi-actions">
        <button
          onClick={onRelayoutBranch}
          disabled={!canRelayout}
          title="Re-layout the selected node's container or dependency cone, keeping everything else fixed"
        >
          Re-layout branch
        </button>
      </div>
    </>
  );
}
