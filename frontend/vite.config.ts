/**
 * @file        frontend/vite.config.ts
 * @purpose     Build config: bundle into kumihimo/server/static with relative
 *              asset paths so the wheel-served page works from any mount, and
 *              proxy /api (including the WebSocket) to a running kumihimo edit
 *              server during `npm run dev`.
 * @layer       frontend
 * @tags        vite, build, proxy
 * @related     kumihimo/server/app.py (serves the build output)
 * @design      PLAN.md §5.1
 */
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  base: "./",
  build: { outDir: "../kumihimo/server/static", emptyOutDir: true },
  server: {
    proxy: { "/api": { target: "http://127.0.0.1:8720", ws: true } },
  },
});
