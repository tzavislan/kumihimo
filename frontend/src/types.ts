/**
 * @file        frontend/src/types.ts
 * @purpose     The TypeScript mirror of the server's payload contract — one
 *              shape, defined once on each side of the wire.
 * @layer       frontend
 * @tags        types, payload, canvas-contract
 * @related     kumihimo/server/payload.py (the Python original)
 * @design      PLAN.md §5.2
 */

export interface LinkRef {
  to: string;
  rel: string;
}

export interface PlanNode {
  digest: string;
  id: string;
  kind: string;
  title: string;
  needs: string[];
  in: string[];
  links: LinkRef[];
  // Mention edges (PLAN2.md §3.2, K30): who's assigned, what skill, who
  // trains it — no ordering semantics, never consulted by any layout.
  agents: string[];
  skills: string[];
  trains: string[];
  priority: number;
  fields: Record<string, unknown>;
  effective: Record<string, unknown>;
  body: string;
}

export interface FieldSpec {
  type: string;
  options: string[];
  required: boolean;
  default: unknown;
}

export interface KindInfo {
  color: string | null;
  fields: Record<string, FieldSpec>;
}

export interface Finding {
  level: "error" | "warning";
  where: string;
  message: string;
}

export interface Position {
  x: number;
  y: number;
}

// K31: one .kumihimo/events.jsonl line — kumihimo/core/ops.py's _log_event
// writes these, actor one of "cli"/"mcp"/"editor"/"api".
export interface EventLogEntry {
  actor: string;
  op: string;
  targets: string[];
}

export interface Payload {
  plan: string;
  description: string;
  strategy: string;
  kinds: Record<string, KindInfo>;
  nodes: PlanNode[];
  findings: Finding[];
  layout: Record<string, Position>;
  // Container ids currently folded to a chip (PLAN2.md §2.3 lens 1) — view
  // state from view.yaml's `collapsed` key, sorted, same sidecar rule as
  // `layout`.
  collapsed: string[];
  // K31: events.jsonl lines new since this server's last rebuild — present
  // (possibly empty) only on a live-socket push (kumihimo/server/watch.py);
  // absent from GET /api/plan and from an op's own POST /api/ops response,
  // since only the watcher path tails the log. attributionDiff.ts is the
  // only reader.
  events?: EventLogEntry[];
}
