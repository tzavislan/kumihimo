---
kind: task
needs: [mcp-tools]
in: [m3-mcp]
effort: S
acceptance:
  - .mcp.json in the repo wires Claude Code to the roadmap plan
  - docs page walks a stranger through connecting
title: Ship .mcp.json and setup docs
status: done
---
Ship .mcp.json pointing kumihimo mcp at plans/roadmap so cloning the repo gives Claude control of the roadmap immediately. Document the setup for any MCP client.