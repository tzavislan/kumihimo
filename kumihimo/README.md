# kumihimo — the package

<!-- BEGIN GENERATED INDEX -- do not edit by hand -->
| file | purpose |
|---|---|
| `__init__.py` | Public entry point of the kumihimo package: the version constant and the re-exported public API (Plan, Node, Finding, KumihimoError). |
<!-- END GENERATED INDEX -->

## What this is

The installable package. `core/` holds the plan model and every operation on
it; `compile/` turns a plan into a prompt (the braid); `cli/`, `server/`, and
`mcp/` are thin clients over `core.ops` — no mutation path bypasses it. The
layout, boundaries, and public API surface are specified in PLAN.md §7.
