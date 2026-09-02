---
kind: task
title: Build the guard
in: [launch]
agents: [wright]
skills: [iteration]
links:
  - {to: ward-postmortem, rel: consult}
effort: M
acceptance:
  - guard rejects the replayed request from the postmortem
---
Implement the rate-limit guard. Check the postmortem before touching the
retry path — that is exactly what broke last time.
