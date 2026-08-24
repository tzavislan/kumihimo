---
kind: risk
title: Redis outage takes limiting down
impact: no rate limiting while Redis is unreachable
mitigation: fail open, alert loudly, coarse per-IP cap at the load balancer as backstop
---
The limiter's state lives in Redis, so a Redis outage is an enforcement
outage. We choose availability: requests flow unlimited, an alert fires, and
the load balancer's coarse per-IP cap holds the line until Redis returns.
