---
kind: question
links:
  - to: editor-conflicts
    rel: informs
  - to: mcp-tools
    rel: informs
title: Concurrent writers policy
---
Should kumihimo mcp auto-detect a running editor server and proxy its ops through it, so one process serializes writes? Cheap to add, slightly magical. PLAN.md 10.5 defaults to no; decide at M4 when both exist.