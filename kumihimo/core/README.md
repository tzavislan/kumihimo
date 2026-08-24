# core — the plan model and operations

<!-- BEGIN GENERATED INDEX -- do not edit by hand -->
| file | purpose |
|---|---|
| `__init__.py` | The plan model and every operation on it: load, validate, order, mutate, save. Imports no CLI, server, MCP, or template code — that boundary is enforced by tes… |
| `errors.py` | The exception vocabulary every layer shares: one base error for expected failures clients turn into messages, and the cycle error that carries its path. |
| `graph.py` | Deterministic structure over the plan DAG: the one topological order the whole system trusts (Kahn with a sorted ready-heap, ties broken by priority then id), … |
| `kinds.py` | The kind system: loads shipped packs, merges manifest overrides into resolved KindDefs, validates node fields against them, and applies defaults. This is where… |
| `model.py` | The pure data model: nodes with their two semantic edge kinds and annotation links, findings, field specs, kind definitions, and the manifest. No IO, no behavi… |
| `plan.py` | The Plan facade — the object users import: load a directory, look at nodes and kinds, check it, save what changed. Orchestrates store and kinds; grows check() … |
| `store.py` | The on-disk truth: locates a plan, parses the manifest and node files (frontmatter round-tripped through ruamel, body kept as raw bytes-in-string), and writes … |
| `validate.py` | Every rule `check` enforces, as findings: unknown/missing kinds, field-schema breaches, dangling edges, the cycle (with its path), orphans, dependencies on sti… |
<!-- END GENERATED INDEX -->

## What this is

Everything that knows what a plan *is*: the node/edge model, kind definitions,
the on-disk store with its byte-fidelity round-trip guarantee, deterministic
graph ordering, validation, and the ops layer that every client (CLI, HTTP,
MCP) calls. Files are the only truth: an op succeeds when the bytes are on
disk. This package imports nothing from `cli/`, `server/`, `mcp/`, or
`compile/`, and no UI, web, or template library — tests enforce it.
