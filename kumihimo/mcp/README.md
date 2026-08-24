# mcp — Claude's handle on a plan

<!-- BEGIN GENERATED INDEX -- do not edit by hand -->
| file | purpose |
|---|---|
| `__init__.py` | The MCP stdio server: ten flat tools over core.ops so an agent can inspect, restructure, and braid a plan. Lands at M3; the package exists now so boundaries an… |
<!-- END GENERATED INDEX -->

## What this is

`kumihimo mcp <plan>` speaks MCP over stdio using the official `mcp` SDK. Ten
tools, flat, no tiers: get_plan, get_node, add_node, update_node, remove_node,
link, unlink, rename_node, check, braid, ready (PLAN.md §6.1). Every tool is a
thin wrapper over `core.ops` — identical behavior to the CLI and editor. Empty
until M3 by design.
