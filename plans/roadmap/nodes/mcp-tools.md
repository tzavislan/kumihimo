---
kind: task
in: [m3-mcp]
effort: M
acceptance:
  - all ten tools behave identically to their CLI/ops twins
  - tool errors surface as MCP errors with the KumihimoError message
title: MCP tool surface
status: done
---
get_plan, get_node, add_node, update_node, remove_node, link, unlink, rename_node, check, braid, ready. Thin wrappers over core.ops — no logic of their own. The ready tool answers: nodes whose needs are all status=done.