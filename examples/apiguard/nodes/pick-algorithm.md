---
kind: decision
title: Rate-limit algorithm
status: settled
choice: sliding-window counter in Redis
---
Token bucket allows bursts that our SLA language forbids; fixed windows
double-spend at boundaries. Sliding-window counter costs one ZSET per key and
we already run Redis for sessions.
