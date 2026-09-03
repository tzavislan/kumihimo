/**
 * @file        frontend/src/Toasts.tsx
 * @purpose     The attribution toast stack (K31): top-right, newest on top,
 *              dismiss-on-click. useAttribution.ts already caps `toasts` at
 *              4 and expires each after ~6s, so this component only renders
 *              — no timers, no state of its own.
 * @layer       frontend
 * @tags        toasts, attribution, notifications
 * @related     frontend/src/useAttribution.ts (owns the toasts state and
 *              its lifetime this renders), frontend/src/styles.css
 *              (.kumi-toast* tokens, both themes), frontend/src/App.tsx
 *              (mounts this once)
 * @design      PLAN2.md §2.5 Motion & attribution, queue item K31
 */
import type { ToastItem } from "./useAttribution";

export interface ToastsProps {
  toasts: ToastItem[];
  onDismiss: (id: number) => void;
}

/** The toast stack; nothing rendered at all while empty. */
export function Toasts({ toasts, onDismiss }: ToastsProps) {
  if (toasts.length === 0) return null;
  return (
    <div className="kumi-toast-stack">
      {toasts.map((toast) => (
        <div key={toast.id} className="kumi-toast" onClick={() => onDismiss(toast.id)}>
          {toast.text}
        </div>
      ))}
    </div>
  );
}
