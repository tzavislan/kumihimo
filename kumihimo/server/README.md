# server — the editor's backend

<!-- BEGIN GENERATED INDEX -- do not edit by hand -->
| file | purpose |
|---|---|
| `__init__.py` | The editor's localhost server: FastAPI app, file watcher, WebSocket push, static frontend assets. Lands at M4; the package exists now so boundaries and layout … |
| `app.py` | The FastAPI application for one plan: GET /api/plan, the /api/ws live socket (initial payload, then every change), and the built frontend served from static/ —… |
| `ops_api.py` | The editor's write path: one op envelope per gesture, validated by a discriminated union of pydantic models, digest-gated against concurrent edits, serialized … |
| `payload.py` | The one JSON shape the canvas consumes: plan meta, every node with raw and effective fields plus body, current findings, the view layout and collapsed-containe… |
| `watch.py` | The file→browser half of the live loop: a broadcaster fanning payloads out to every connected WebSocket, and the watchfiles task that rebuilds and publishes on… |
<!-- END GENERATED INDEX -->

## What this is

`kumihimo edit` starts this: a localhost-only FastAPI app that watches the plan
directory, pushes re-parsed plans over a WebSocket, and applies editor
operations through `core.ops`. The built frontend is served from `static/`
(gitignored; CI builds it from `frontend/`). Empty until M4 by design.
