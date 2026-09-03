/**
 * @file        frontend/src/useAttribution.ts
 * @purpose     K31: owns the plan subscription — the initial fetch plus the
 *              live socket, superseding App.tsx's old bare
 *              `openLive(setPayload)` — diffing each live push against the
 *              one before it via attributionDiff.ts and turning the result
 *              into toast state (id-tagged, ~6s auto-dismiss, capped at 4
 *              kept, newest first) and a pulsing-node-id set. Under normal
 *              motion a node's own pulse clears on its card's animationend
 *              (KumiNode.tsx/KumiGroupNode.tsx's onAnimationEnd, threaded
 *              through node data exactly like onToggleCollapse already is)
 *              via onPulseEnd below; fix round: under
 *              prefers-reduced-motion no animation ever plays, so that
 *              event never fires — ids are simply never added to
 *              pulsingIds in the first place when reduced motion is active
 *              (styles.css already renders no ring there either way, so
 *              this changes nothing visible), rather than adding them and
 *              relying on a clear that can never come.
 * @layer       frontend
 * @tags        attribution, events, toasts, pulse, live, hook
 * @related     frontend/src/attributionDiff.ts (the pure diff/classify this
 *              wraps in state), frontend/src/Toasts.tsx (renders `toasts`),
 *              frontend/src/canvasBuild.ts (reads `pulsingIds`, embeds a
 *              per-node onPulseEnd closure into each node's data),
 *              frontend/src/App.tsx (the sole caller — one hook call
 *              replaces its old fetch/live effect entirely)
 * @design      PLAN2.md §2.5 Motion & attribution, queue item K31
 */
import { useCallback, useEffect, useRef, useState } from "react";
import { fetchPlan, openLive } from "./api";
import { diffLivePayload } from "./attributionDiff";
import type { Payload } from "./types";

export interface ToastItem {
  id: number;
  text: string;
}

const MAX_TOASTS = 4;
const TOAST_LIFETIME_MS = 6000;

// Queried live (not cached) since the OS setting can change mid-session;
// mirrors theme.ts's own plain, unguarded window.matchMedia call.
function prefersReducedMotion(): boolean {
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

export interface Attribution {
  toasts: ToastItem[];
  dismissToast: (id: number) => void;
  pulsingIds: Set<string>;
  onPulseEnd: (id: string) => void;
}

/** Subscribes to the plan and hands every payload to `setPayload`, exactly
 * as App.tsx did before this existed — plus, for every live-socket push,
 * the K31 toast/pulse state this returns. */
export function useAttribution(setPayload: (payload: Payload) => void): Attribution {
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const [pulsingIds, setPulsingIds] = useState<Set<string>>(new Set());
  // The live socket's own previous message — never the initial fetchPlan()
  // GET, so the socket's first message (the same current state fetchPlan
  // just got, not a "change") always diffs to nothing and simply seeds this.
  const previous = useRef<Payload | null>(null);
  const nextToastId = useRef(0);

  const dismissToast = useCallback((id: number) => {
    setToasts((prev) => prev.filter((toast) => toast.id !== id));
  }, []);

  const onPulseEnd = useCallback((id: string) => {
    setPulsingIds((prev) => {
      if (!prev.has(id)) return prev;
      const next = new Set(prev);
      next.delete(id);
      return next;
    });
  }, []);

  useEffect(() => {
    fetchPlan().then(setPayload).catch(console.error);
    return openLive((incoming) => {
      const result = diffLivePayload(previous.current, incoming);
      previous.current = incoming;
      if (result.toastTexts.length > 0) {
        const fresh = result.toastTexts.map((text) => ({ id: nextToastId.current++, text }));
        for (const toast of fresh) setTimeout(() => dismissToast(toast.id), TOAST_LIFETIME_MS);
        setToasts((prev) => [...fresh, ...prev].slice(0, MAX_TOASTS));
      }
      if (result.pulseIds.size > 0 && !prefersReducedMotion()) {
        setPulsingIds((prev) => new Set([...prev, ...result.pulseIds]));
      }
      setPayload(incoming);
    });
  }, [setPayload, dismissToast]);

  return { toasts, dismissToast, pulsingIds, onPulseEnd };
}
