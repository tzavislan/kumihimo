# frontend — the editor's build tooling

<!-- BEGIN GENERATED INDEX -- do not edit by hand -->
| file | purpose |
|---|---|
| `vite.config.ts` | Build config: bundle into kumihimo/server/static with relative asset paths so the wheel-served page works from any mount, proxy /api (including the WebSocket) … |
<!-- END GENERATED INDEX -->

## What this is

The visual editor (M4): a Vite + React app. This top level holds project and
build files only — `vite.config.ts` (the one file `tools/lint.py` scans at
this level; see [src/](src/README.md) for the application itself),
`tsconfig.json`, `package.json`/`package-lock.json`, and `index.html`.

`npm run dev` serves the app against a running `kumihimo serve` backend,
proxying `/api` — WebSocket included, per `vite.config.ts` — to it. `npm run
build` bundles into `kumihimo/server/static/`, which is what the wheel ships
and `kumihimo/server/app.py` mounts directly; there is no separate frontend
deploy step, and no build output is committed. `npm run typecheck` runs `tsc
--noEmit` against `tsconfig.json`'s `strict` config — a separate step from
`build`, since Vite's own build does not type-check. CI's `frontend` job runs
both on every push; the root `checks` job's `tools/lint.py` separately covers
header/purpose/file-cap conventions over this same TypeScript, the same way
it covers the Python packages.
