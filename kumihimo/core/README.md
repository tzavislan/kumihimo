# core — the plan model and operations

<!-- BEGIN GENERATED INDEX -- do not edit by hand -->
| file | purpose |
|---|---|
| `__init__.py` | The plan model and every operation on it: load, validate, order, mutate, save. Imports no CLI, server, MCP, or template code — that boundary is enforced by tes… |
<!-- END GENERATED INDEX -->

## What this is

Everything that knows what a plan *is*: the node/edge model, kind definitions,
the on-disk store with its byte-fidelity round-trip guarantee, deterministic
graph ordering, validation, and the ops layer that every client (CLI, HTTP,
MCP) calls. Files are the only truth: an op succeeds when the bytes are on
disk. This package imports nothing from `cli/`, `server/`, `mcp/`, or
`compile/`, and no UI, web, or template library — tests enforce it.
