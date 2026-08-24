# server — the editor's backend

<!-- BEGIN GENERATED INDEX -- do not edit by hand -->
| file | purpose |
|---|---|
| `__init__.py` | The editor's localhost server: FastAPI app, file watcher, WebSocket push, static frontend assets. Lands at M4; the package exists now so boundaries and layout … |
<!-- END GENERATED INDEX -->

## What this is

`kumihimo edit` starts this: a localhost-only FastAPI app that watches the plan
directory, pushes re-parsed plans over a WebSocket, and applies editor
operations through `core.ops`. The built frontend is served from `static/`
(gitignored; CI builds it from `frontend/`). Empty until M4 by design.
