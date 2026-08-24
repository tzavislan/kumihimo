/**
 * @file        frontend/src/KumiNode.tsx
 * @purpose     The one custom React Flow node: kind-colored edge stripe, title,
 *              id, and a kind pill; milestones read as section headers.
 * @layer       frontend
 * @tags        react-flow, node, kind-colors
 * @related     frontend/src/App.tsx (registers this as node type "kumi")
 * @design      PLAN.md §5.3
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
      <Handle type="target" position={FlowPosition.Left} />
      <div className="kumi-title">{node.title}</div>
      <div className="kumi-meta">
        <span className="kumi-pill" style={{ background: color }}>
          {node.kind || "?"}
        </span>
        {status ? <span className="kumi-status">{status}</span> : null}
        <span className="kumi-id">{node.id}</span>
      </div>
      <Handle type="source" position={FlowPosition.Right} />
    </div>
  );
}
