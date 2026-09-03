/**
 * @file        frontend/vite.config.ts
 * @purpose     Build config: bundle into kumihimo/server/static with relative
 *              asset paths so the wheel-served page works from any mount,
 *              proxy /api (including the WebSocket) to a running kumihimo
 *              edit server during `npm run dev`, and split the output so the
 *              INITIAL cold-load payload stays small (K34): react/react-dom/
 *              @xyflow(+its own zustand/classcat deps) land in one "vendor"
 *              chunk — eager like the app-code chunk, but its own cache
 *              entry, so a pure app-code change (which is most iterations
 *              here) doesn't invalidate it — while elkjs gets its OWN named
 *              chunk ("elk") kept deliberately separate from vendor: grouping
 *              it into an eagerly-loaded chunk would force-load it on every
 *              page view and defeat layout.ts's dynamic import entirely.
 *              marked (K33) needs no entry here — a plain top-level
 *              `import("marked")` already gets it its own lazy chunk with
 *              zero manualChunks config, verified in the K33 build log.
 *              Vite's build still prints its own "chunks larger than 500 kB"
 *              warning for elk-*.js (~1.4MB minified, elkjs's own bundled
 *              size, confirmed unavoidable short of patching the library) —
 *              a deliberate, justified case rather than a regression to
 *              chase: that chunk is never part of the initial payload (this
 *              file's whole point), and raising chunkSizeWarningLimit
 *              globally to silence it would just as quietly hide a future
 *              regression in vendor or the app's own index chunk, which
 *              SHOULD warn well before 500 kB.
 * @layer       frontend
 * @tags        vite, build, proxy, code-splitting, manual-chunks, elk, vendor
 * @related     kumihimo/server/app.py (serves the build output),
 *              frontend/src/layout.ts (elkjs's dynamic import — the "elk"
 *              chunk this only NAMES, never makes eager)
 * @design      PLAN.md §5.1, queue item K34
 */
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  base: "./",
  build: {
    outDir: "../kumihimo/server/static",
    emptyOutDir: true,
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (!id.includes("node_modules")) return undefined;
          if (id.includes("node_modules/elkjs")) return "elk";
          if (
            id.includes("node_modules/react/") ||
            id.includes("node_modules/react-dom") ||
            id.includes("node_modules/scheduler") ||
            id.includes("node_modules/@xyflow") ||
            id.includes("node_modules/zustand") ||
            id.includes("node_modules/classcat")
          ) {
            return "vendor";
          }
          return undefined;
        },
      },
    },
  },
  server: {
    proxy: { "/api": { target: "http://127.0.0.1:8720", ws: true } },
  },
});
