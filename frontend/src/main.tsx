/**
 * @file        frontend/src/main.tsx
 * @purpose     Entry point: mount App under #root.
 * @layer       frontend
 * @tags        entry, react
 * @related     frontend/src/App.tsx (everything)
 * @design      PLAN.md §5.1
 */
import { createRoot } from "react-dom/client";
import App from "./App";
import "./styles.css";

const container = document.getElementById("root");
if (container) {
  createRoot(container).render(<App />);
}
