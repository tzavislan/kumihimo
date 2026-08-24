---
kind: task
title: v2 endpoint surface
in: [ship-guarded-api]
effort: S
acceptance:
  - every route listed with auth requirement and limit tier
  - reviewed by the platform team
---
Define the v2 endpoint surface: which routes exist, which are authenticated,
and which carry per-key limits. The limiter hangs off this map, so it lands
first.
