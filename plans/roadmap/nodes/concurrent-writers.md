---
kind: question
links:
  - to: editor-conflicts
    rel: informs
  - to: mcp-tools
    rel: informs
title: Concurrent writers policy
status: answered
answer: No proxy in v0.1. Files-as-truth plus the server's single-writer lock and digest 409s bound the damage to one field edit; MCP and vim race at last-write-wins file level by design. Revisit only if real corruption is observed.
---
Should kumihimo mcp auto-detect a running editor server and proxy its ops through it, so one process serializes writes? Cheap to add, slightly magical. PLAN.md 10.5 defaults to no; decide at M4 when both exist.