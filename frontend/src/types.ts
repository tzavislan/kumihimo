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
  id: string;
  kind: string;
  title: string;
  needs: string[];
  in: string[];
  links: LinkRef[];
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

export interface Payload {
  plan: string;
  description: string;
  strategy: string;
  kinds: Record<string, KindInfo>;
  nodes: PlanNode[];
  findings: Finding[];
  layout: Record<string, Position>;
}
