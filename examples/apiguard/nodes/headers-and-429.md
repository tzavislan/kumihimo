---
kind: task
title: Limit headers and 429 body
needs: [rate-limit-core]
in: [ship-guarded-api]
effort: S
acceptance:
  - X-RateLimit-Limit/Remaining/Reset on every limited route
  - 429 body links the public rate-limit docs
---
Honest clients need to see the wall before they hit it: emit the standard
X-RateLimit-* headers on every limited response, and make the 429 body point
at the documentation instead of being a bare status.
