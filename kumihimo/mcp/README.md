# mcp — Claude's handle on a plan

<!-- BEGIN GENERATED INDEX -- do not edit by hand -->
| file | purpose |
|---|---|
| `__init__.py` | The MCP stdio server: ten flat tools over core.ops so an agent can inspect, restructure, and braid a plan. Lands at M3; the package exists now so boundaries an… |
| `server.py` | Builds the MCPServer stdio server for one plan root: eleven tools, flat, no tiers, each a closure over tools.py. KumihimoErrors propagate as tool errors carryi… |
| `tools.py` | The MCP tools' actual behavior, as plain functions over a plan root — thin twins of the ops layer plus the read/braid/ready queries, returning JSON-shaped dict… |
<!-- END GENERATED INDEX -->

## What this is

`kumihimo mcp <plan>` speaks MCP over stdio using the official `mcp` SDK
(2.x, `MCPServer`). Eleven tools, flat, no tiers: get_plan, get_node,
add_node, update_node, remove_node, link, unlink, rename_node, check, braid,
ready (PLAN.md §6.1 — which says "ten"; it lists eleven, and the count in
prose was the error). `tools.py` holds the behavior as plain functions so
tests pin them to their ops/CLI twins; `server.py` only registers. The repo's
`.mcp.json` serves `plans/roadmap`, so cloning gives Claude the roadmap.
