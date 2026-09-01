/**
 * @file        frontend/src/theme.ts
 * @purpose     Light/dark theme (PLAN2.md §2.5): init from localStorage or
 *              OS preference, persist on change, toggle. The DOM write
 *              (data-theme on <html>) is the one place that sets it, so
 *              toggle and persistence can never drift apart — styles.css
 *              does the rest via [data-theme="dark"].
 * @layer       frontend
 * @tags        theme, dark-mode, hook
 * @related     frontend/src/App.tsx (mounts useTheme, wires the sidebar
 *              toggle button and the palette's "Toggle theme" command to it),
 *              frontend/src/styles.css (the tokens data-theme switches)
 * @design      PLAN2.md §2.5
 */
import { useCallback, useEffect, useState } from "react";

const THEME_KEY = "kumi-theme";
export type Theme = "light" | "dark";

// Storage wins once the user has chosen; before that, follow the OS so a
// fresh install doesn't default to a jarring light canvas on a dark desktop.
function initialTheme(): Theme {
  const stored = localStorage.getItem(THEME_KEY);
  if (stored === "light" || stored === "dark") return stored;
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

/** The active theme and a toggle. Mount once per app; the effect inside
 * keeps the DOM attribute and localStorage in sync with every change. */
export function useTheme(): { theme: Theme; toggleTheme: () => void } {
  const [theme, setTheme] = useState<Theme>(initialTheme);

  // The attribute, not the state value, is what styles.css keys off of —
  // this is the one place that writes it, so toggle and persistence can't
  // drift apart.
  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem(THEME_KEY, theme);
  }, [theme]);

  const toggleTheme = useCallback(() => {
    setTheme((current) => (current === "dark" ? "light" : "dark"));
  }, []);

  return { theme, toggleTheme };
}
