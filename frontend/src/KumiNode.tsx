/**
 * @file        frontend/src/KumiNode.tsx
 * @purpose     The one custom React Flow node: kind-colored edge stripe,
 *              title, id, and a kind pill; milestones read as section
 *              headers. Renders one of three semantic-zoom tiers (far/mid/
 *              near), chosen upstream in App.tsx from viewport.zoom and
 *              handed down through node data.
 * @layer       frontend
 * @tags        react-flow, node, kind-colors, semantic-zoom, findings
 * @related     frontend/src/App.tsx (registers this as node type "kumi",
 *              tracks the active tier and passes it through node data; also
 *              sets the wrapper's kumi-halo-error/warning class this file's
 *              .kumi-node div is the box-shadow target for — styles.css)
 * @design      PLAN.md §5.3, PLAN2.md §2.2, §2.4
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

// Semantic zoom (PLAN2.md §2.2): three tiers switched on React Flow's
// viewport.zoom. Thresholds live here, beside the rendering that branches on
// them, so App.tsx's viewport listener and this file's tiers can never drift
// apart into disagreeing about where a boundary falls.
export type ZoomTier = "far" | "mid" | "near";

export function zoomTier(zoom: number): ZoomTier {
  if (zoom < 0.45) return "far";
  if (zoom < 1.3) return "mid";
  return "near";
}

const STATUS_GLYPH: Record<string, string> = {
  todo: "○",
  doing: "◐",
  done: "●",
  blocked: "⛔",
};

export interface KumiNodeData extends Record<string, unknown> {
  node: PlanNode;
  color: string;
  tier: ZoomTier;
  // How many payload nodes name this node in their `in` — App.tsx computes
  // this once per payload over every node rather than here, since this
  // component only ever sees one node at a time. Shown only for
  // milestone-kind nodes (mid/near), but always populated so this file stays
  // the single place deciding what's visible.
  memberCount: number;
  // effective.acceptance, kept only when it actually resolved to a list
  // (kinds.yaml's "list" field type) — App.tsx checks the shape once so this
  // component never has to re-validate it on every render.
  acceptance: string[] | null;
}

/** The four ports, one per edge kind (PLAN2.md §2.4): needs runs left/right,
 * in/link run top/bottom, so membership stops fighting dependencies for the
 * same two pixels. Ids must match STATIC_HANDLES in edges.ts and the
 * sourceHandle/targetHandle buildEdges sets on each edge.
 *
 * Mounted at every zoom tier, far tier included: React Flow resolves an edge
 * against the node's actual handle DOM, not against what a tier chooses to
 * draw, so unmounting these at far tier would silently break every edge
 * touching a zoomed-out node (and the drag-to-connect Playwright smoke
 * test). Far tier only shrinks them visually — .kumi-tier-far
 * .react-flow__handle in styles.css — never display:none/pointer-events. */
function EdgeHandles() {
  return (
    <>
      <Handle type="target" position={FlowPosition.Left} id="in-left" />
      <Handle type="source" position={FlowPosition.Right} id="out-right" />
      <Handle type="target" position={FlowPosition.Top} id="in-top" />
      <Handle type="source" position={FlowPosition.Bottom} id="out-bottom" />
    </>
  );
}

/** Render one plan node on the canvas, at the tier App.tsx has picked. */
export function KumiNode(props: NodeProps) {
  const { node, color, tier, memberCount, acceptance } = props.data as KumiNodeData;
  const isMilestone = node.kind === "milestone";
  const status = typeof node.effective.status === "string" ? node.effective.status : null;
  const effort = typeof node.effective.effort === "string" ? node.effective.effort : null;
  const glyph = status ? STATUS_GLYPH[status] : undefined;

  if (tier === "far") {
    // The plan's silhouette (PLAN2.md §2.2): a colored chip, title only, no
    // pill/status/id. NODE_WIDTH/NODE_HEIGHT (layout.ts) never change per
    // tier — elk already laid the whole plan out against those numbers, and
    // edges.ts's STATIC_HANDLES coordinates assume the same fixed box at
    // every tier. So the box below stays the full 210x66; the chip reads as
    // compact by sitting smaller *inside* it (base .kumi-node padding plus
    // the chip's own), not by the node shrinking.
    return (
      <div className="kumi-node kumi-tier-far" title={node.title}>
        <EdgeHandles />
        <div
          className="kumi-chip"
          // Data-derived color, not a token: the same narrow exception
          // derive.ts's minimapNodeColor already carves out. The tint has to
          // be *this node's* kind color (task/milestone/plan-override), and
          // there's no --kumi-* var for a color that only exists at runtime.
          // Text stays on var(--kumi-text) so legibility never rides on it.
          style={{ background: `${color}26`, borderColor: color }}
        >
          {node.title}
        </div>
      </div>
    );
  }

  return (
    <div
      className={`kumi-node kumi-tier-${tier}${isMilestone ? " kumi-milestone" : ""}`}
      style={{ borderLeftColor: color }}
    >
      <EdgeHandles />
      <div className="kumi-title">{node.title}</div>
      <div className="kumi-meta">
        <span className="kumi-pill" style={{ background: color }}>
          {node.kind || "?"}
        </span>
        {/* Additive, not a replacement (PLAN2.md §2.2 mid tier): the glyph
            is new; the text status beside it is exactly what rendered
            before this tier work landed. */}
        {glyph ? (
          <span className="kumi-status-glyph" title={status ?? undefined}>
            {glyph}
          </span>
        ) : null}
        {status ? <span className="kumi-status">{status}</span> : null}
        {effort ? <span className="kumi-effort-chip">{effort}</span> : null}
        {isMilestone ? (
          <span className="kumi-member-badge">
            {memberCount} thread{memberCount === 1 ? "" : "s"}
          </span>
        ) : null}
        <span className="kumi-id">{node.id}</span>
      </div>
      {/* Near tier (PLAN2.md §2.2, tightened after critic feedback: an
          earlier draft let this grow past 66px and fused with whatever elk
          placed 40px below on the roadmap plan). styles.css now hard-caps
          this box at height:66px with overflow hidden, so content is one
          line each, sized to actually fit rather than to lean on the clip:
          a body preview line, and an acceptance summary — first item plus a
          "+n more" count — instead of a multi-item list. */}
      {tier === "near" ? (
        <>
          {node.body.trim() ? <div className="kumi-body-preview">{node.body}</div> : null}
          {acceptance && acceptance.length > 0 ? (
            <div className="kumi-acceptance-preview">
              <span className="kumi-acceptance-item">☐ {acceptance[0]}</span>
              {acceptance.length > 1 ? (
                <span className="kumi-acceptance-more">+{acceptance.length - 1} more</span>
              ) : null}
            </div>
          ) : null}
        </>
      ) : null}
    </div>
  );
}
