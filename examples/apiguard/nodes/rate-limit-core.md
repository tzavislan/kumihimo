---
kind: task
title: Rate-limit middleware
needs: [api-endpoints, pick-algorithm]
in: [ship-guarded-api]
effort: M
acceptance:
  - 429 + Retry-After on breach
  - overhead under 2ms p99 at 1k rps
links:
  - {to: redis-outage, rel: threatened-by}
---
Middleware on every authenticated route. Read the key's window from Redis,
increment, compare against the tier limit. Fail *open* on Redis errors —
availability beats enforcement; see redis-outage for the standing mitigation.
