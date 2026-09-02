/**
 * @file        frontend/src/KumiGroupNode.tsx
 * @purpose     The container React Flow node (PLAN2.md §2.3 lens 1): any
 *              node with members renders as this instead of KumiNode.tsx's
 *              leaf card. Two looks, chosen by data.collapsed rather than by
 *              zoom tier (containers keep one look across tiers this pass):
 *              expanded is a titled frame — sized and positioned upstream by
 *              containers.ts's boundingBox, empty inside so the member cards
 *              React Flow places there read as nested — and collapsed is a
 *              normal-card-sized chip carrying the n/m done count and member
 *              total that would otherwise vanish along with the members.
 *              Both mount the toggle button and the shared four-port handles
 *              so the container is a real edge endpoint either way. Its two
 *              kind-pill spans take `pillText` alongside `color` (K30 fix
 *              round): undefined outside a Crew-lens tint, so the pill's
 *              usual --kumi-pill-text token applies unchanged; only a
 *              tinted pill gets its own contrast-checked override.
 * @layer       frontend
 * @tags        react-flow, node, containers, collapse, semantic-zoom
 * @related     frontend/src/containers.ts (builds this node's data via
 *              buildContainerNode; the n/m done and member-list math),
 *              frontend/src/KumiNode.tsx (EdgeHandles, reused verbatim),
 *              frontend/src/App.tsx (registers this as node type
 *              "kumiGroup", wires onToggle to the set_collapsed op),
 *              frontend/src/styles.css (.kumi-group-* rules; .kumi-node
 *              itself is shared with KumiNode.tsx so halos/cones/selection
 *              apply for free)
 * @design      PLAN2.md §2.3 lens 1
 */
import type { NodeProps } from "@xyflow/react";
import { EdgeHandles } from "./KumiNode";
import type { PlanNode } from "./types";

export interface KumiGroupNodeData extends Record<string, unknown> {
  node: PlanNode;
  color: string;
  // Readable text color for the kind pill's background when `color` is a
  // Crew-lens tint (fix round, containers.ts's buildContainerNode) —
  // undefined otherwise, so the pill falls back to its usual
  // --kumi-pill-text token unchanged.
  pillText: string | undefined;
  collapsed: boolean;
  done: number;
  total: number;
  // Fired by the ▸/▾ button only — double-click still means focus, same as
  // any other node, so the toggle stops its own click from also selecting.
  onToggle: () => void;
}

/** Render one container, expanded (a frame around its members) or collapsed
 * (a chip standing in for all of them). */
export function KumiGroupNode(props: NodeProps) {
  const { node, color, pillText, collapsed, done, total, onToggle } = props.data as KumiGroupNodeData;
  const kind = node.kind || "?";
  const progress = `${done}/${total} done`;

  const header = (
    <div className="kumi-group-header">
      <button
        className="kumi-group-toggle"
        onClick={(event) => {
          event.stopPropagation();
          onToggle();
        }}
        title={collapsed ? "Expand" : "Collapse"}
        aria-label={collapsed ? "Expand" : "Collapse"}
      >
        {collapsed ? "▸" : "▾"}
      </button>
      <span className="kumi-title">{node.title}</span>
      {collapsed ? null : (
        <>
          {/* pillText undefined outside a Crew-lens tint -> falls through
              to the CSS token, same as KumiNode.tsx's leaf pill. */}
          <span className="kumi-pill" style={{ background: color, color: pillText }}>
            {kind}
          </span>
          <span className="kumi-group-progress">{progress}</span>
        </>
      )}
    </div>
  );

  if (collapsed) {
    return (
      <div className="kumi-node kumi-group kumi-group-collapsed" style={{ borderLeftColor: color }}>
        <EdgeHandles />
        {header}
        <div className="kumi-meta">
          <span className="kumi-pill" style={{ background: color, color: pillText }}>
            {kind}
          </span>
          <span className="kumi-group-progress">{progress}</span>
          <span className="kumi-member-badge">
            {total} member{total === 1 ? "" : "s"}
          </span>
        </div>
      </div>
    );
  }

  return (
    <div
      className="kumi-node kumi-group kumi-group-expanded"
      // Same data-derived-color-at-low-alpha exception KumiNode.tsx's
      // far-tier chip already carves out of the tokens-only rule — there's
      // no --kumi-* var for a color that only exists at runtime.
      style={{ background: `${color}14`, borderColor: color }}
    >
      <EdgeHandles />
      {header}
    </div>
  );
}
