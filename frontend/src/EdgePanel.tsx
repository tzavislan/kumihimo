/**
 * @file        frontend/src/EdgePanel.tsx
 * @purpose     The sidebar's edge panel: the selected edge's sentence, a jump
 *              button per endpoint, and Remove edge — mention edges included.
 *              Purely presentational, the same split as NodeForm.tsx: App.tsx
 *              owns selectedEdge/selectedEdgeInfo state and the jump/apply
 *              callbacks, this only renders. Pulled out of App.tsx to make
 *              room under the line cap for K32's undo trail.
 * @layer       frontend
 * @tags        form, edges, sidebar
 * @related     frontend/src/App.tsx (owns selectedEdge state, mounts this),
 *              frontend/src/edges.ts (edgeSentence/unlinkEnvelope/EdgeInfo —
 *              the shape and behavior this renders/invokes),
 *              frontend/src/derive.ts (nodeTitle)
 * @design      PLAN.md §5.3, PLAN2.md §2.4
 */
import { nodeTitle } from "./derive";
import { edgeSentence, unlinkEnvelope, type EdgeInfo } from "./edges";
import type { Payload } from "./types";

export interface EdgePanelProps {
  payload: Payload;
  edgeId: string;
  info: EdgeInfo;
  onJump: (nodeId: string) => void;
  onApply: (envelope: Record<string, unknown>) => void;
  onClose: () => void;
}

/** The selected edge's sentence, jump-to-endpoint buttons, and Remove edge. */
export function EdgePanel({ payload, edgeId, info, onJump, onApply, onClose }: EdgePanelProps) {
  return (
    <div className="kumi-edge-panel">
      <p className="kumi-edge-sentence">{edgeSentence(payload, info)}</p>
      <div className="kumi-actions">
        <button onClick={() => onJump(info.from)}>↷ {nodeTitle(payload, info.from)}</button>
        <button onClick={() => onJump(info.to)}>↷ {nodeTitle(payload, info.to)}</button>
      </div>
      <div className="kumi-actions">
        <button
          onClick={() => {
            const envelope = unlinkEnvelope(edgeId);
            if (envelope) onApply(envelope);
            onClose();
          }}
        >
          Remove edge
        </button>
      </div>
    </div>
  );
}
