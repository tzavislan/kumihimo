/**
 * @file        frontend/src/api.ts
 * @purpose     The wire: fetch the initial payload, then hold a WebSocket that
 *              delivers every change, reconnecting quietly when the server
 *              restarts.
 * @layer       frontend
 * @tags        fetch, websocket, reconnect
 * @related     kumihimo/server/app.py (the endpoints this speaks to)
 * @design      PLAN.md §5.2
 */
import type { Payload } from "./types";

/** Fetch the current payload once. */
export async function fetchPlan(): Promise<Payload> {
  const response = await fetch("/api/plan");
  if (!response.ok) throw new Error(`GET /api/plan -> ${response.status}`);
  return (await response.json()) as Payload;
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
