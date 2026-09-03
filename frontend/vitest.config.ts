/**
 * @file        frontend/vitest.config.ts
 * @purpose     vitest config for the pure-function test suite (K44): the
 *              "node" test environment — every target (lenses.ts's WCAG/hue
 *              math, attributionDiff.ts's diff/claim logic, braidPreview.ts's
 *              urlScheme table, cones.ts's BFS) is plain TypeScript with no
 *              DOM, so jsdom/happy-dom would be dead weight this repo has no
 *              other reason to depend on. Scoped to *.test.ts next to their
 *              sources (this repo's existing "tests live beside what they
 *              cover" convention, not a separate tests/ tree) — no *.test.tsx
 *              yet, since no component test exists; widening the glob when
 *              one is added is a one-line change here.
 * @layer       frontend
 * @tags        vitest, testing, config
 * @related     frontend/package.json ("test": "vitest run"),
 *              frontend/src/*.test.ts (the suite this config runs),
 *              .github/workflows/ci.yml (the frontend job's Test step)
 * @design      PLAN.md §7.3, queue item K44
 */
import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    environment: "node",
    include: ["src/**/*.test.ts"],
  },
});
