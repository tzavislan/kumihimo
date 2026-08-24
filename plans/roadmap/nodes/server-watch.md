---
kind: task
in: [m4-canvas]
effort: M
acceptance:
  - file edit reflected over the WebSocket in under a second
  - server binds localhost only
title: Watching plan server
---
FastAPI app serving the plan as JSON plus a WebSocket that pushes the full re-parsed plan on any change under the plan root (watchfiles, debounced). The filesystem is the bus; there is no server-side document state.