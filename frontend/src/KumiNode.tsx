/**
 * @file        frontend/src/KumiNode.tsx
 * @purpose     The one custom React Flow node: kind-colored edge stripe, title,
 *              id, and a kind pill; milestones read as section headers.
 * @layer       frontend
 * @tags        react-flow, node, kind-colors
 * @related     frontend/src/App.tsx (registers this as node type "kumi")
 * @design      PLAN.md §5.3, PLAN2.md §2.4
 */
import { Handle, Position as FlowPosition, type NodeProps } from "@xyflow/react";
import type { PlanNode } from "./types";

export const KIND_COLORS: Record<string, string> = {
  task: "#3b82f6",
  milestone: "#8b5cf6",
  decision: "#f59e0b",
  risk: "#ef4444",
  question: "#14b8a6",
};

export const FALLBACK_COLOR = "#6b7280";

export interface KumiNodeData extends Record<string, unknown> {
  node: PlanNode;
  color: string;
}

/** Render one plan node on the canvas. */
export function KumiNode(props: NodeProps) {
  const { node, color } = props.data as KumiNodeData;
  const isMilestone = node.kind === "milestone";
  const status = typeof node.effective.status === "string" ? node.effective.status : null;
  return (
    <div className={`kumi-node${isMilestone ? " kumi-milestone" : ""}`} style={{ borderLeftColor: color }}>
      {/* Four ports, one per edge kind (PLAN2.md §2.4): needs runs left/right,
          in/link run top/bottom, so membership stops fighting dependencies
          for the same two pixels. Ids must match STATIC_HANDLES in App.tsx
          and the sourceHandle/targetHandle buildEdges sets on each edge. */}
      <Handle type="target" position={FlowPosition.Left} id="in-left" />
      <Handle type="source" position={FlowPosition.Right} id="out-right" />
      <Handle type="target" position={FlowPosition.Top} id="in-top" />
      <Handle type="source" position={FlowPosition.Bottom} id="out-bottom" />
      <div className="kumi-title">{node.title}</div>
      <div className="kumi-meta">
        <span className="kumi-pill" style={{ background: color }}>
          {node.kind || "?"}
        </span>
        {status ? <span className="kumi-status">{status}</span> : null}
        <span className="kumi-id">{node.id}</span>
      </div>
    </div>
  );
}
