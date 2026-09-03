/**
 * @file        frontend/src/api.ts
 * @purpose     The wire: fetch the initial payload, then hold a WebSocket that
 *              delivers every change, reconnecting quietly when the server
 *              restarts. postOp's success shape also carries the K32 inverse
 *              envelope, its digest preconditions, and a human label —
 *              kumihimo/server/ops_api.py's OpOutcome, merged into every
 *              /api/ops response — for the caller to hand to useUndoTrail.ts.
 * @layer       frontend
 * @tags        fetch, websocket, reconnect, undo
 * @related     kumihimo/server/app.py (the endpoints this speaks to),
 *              kumihimo/server/ops_api.py (OpOutcome — the inverse/
 *              preconditions/label shape postOp's success case mirrors),
 *              frontend/src/useUndoTrail.ts (the sole reader of those three)
 * @design      PLAN.md §5.2, PLAN2.md §2.5 Undo trail, queue item K32
 */
import type { Payload } from "./types";
import type { Precondition } from "./useUndoTrail";

/** Fetch the current payload once. */
export async function fetchPlan(): Promise<Payload> {
  const response = await fetch("/api/plan");
  if (!response.ok) throw new Error(`GET /api/plan -> ${response.status}`);
  return (await response.json()) as Payload;
}

export interface OpError {
  status: number;
  detail: string;
}

export type OpResult =
  | {
      ok: true;
      payload: Payload;
      // K32: null inverse means honestly not undoable (remove_node) — see
      // OpOutcome's own doc comment for why preconditions is then always [].
      inverse: Record<string, unknown> | null;
      preconditions: Precondition[];
      label: string;
    }
  | ({ ok: false } & OpError);

/** POST one op envelope; 409 means stale (refresh), 400 carries the message. */
export async function postOp(envelope: Record<string, unknown>): Promise<OpResult> {
  const response = await fetch("/api/ops", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(envelope),
  });
  if (!response.ok) {
    let detail = `HTTP ${response.status}`;
    try {
      const body = (await response.json()) as { detail?: unknown };
      if (typeof body.detail === "string") detail = body.detail;
      else if (body.detail) detail = JSON.stringify(body.detail);
    } catch {
      /* keep the fallback */
    }
    return { ok: false, status: response.status, detail };
  }
  const body = (await response.json()) as Payload & {
    inverse: Record<string, unknown> | null;
    preconditions: Precondition[];
    label: string;
  };
  const { inverse, preconditions, label, ...payload } = body;
  return { ok: true, payload: payload as Payload, inverse, preconditions, label };
}

/** Fetch the compiled braid text (throws with the server's message on 400). */
export async function fetchBraid(): Promise<string> {
  const response = await fetch("/api/braid");
  const text = await response.text();
  if (!response.ok) throw new Error(text);
  return text;
}

/** Which plan files differ from git HEAD, when tracked. */
export async function fetchDirty(): Promise<{ tracked: boolean; dirty: string[] }> {
  const response = await fetch("/api/dirty");
  return (await response.json()) as { tracked: boolean; dirty: string[] };
}

/**
 * Open the live socket; every payload goes to onPayload. Reconnects after two
 * seconds on close. Returns a stop function.
 */
export function openLive(onPayload: (payload: Payload) => void): () => void {
  let socket: WebSocket | null = null;
  let stopped = false;
  const protocol = location.protocol === "https:" ? "wss" : "ws";

  const connect = () => {
    if (stopped) return;
    socket = new WebSocket(`${protocol}://${location.host}/api/ws`);
    socket.onmessage = (event) => {
      onPayload(JSON.parse(event.data as string) as Payload);
    };
    socket.onclose = () => {
      if (!stopped) setTimeout(connect, 2000);
    };
  };
  connect();
  return () => {
    stopped = true;
    socket?.close();
  };
}
