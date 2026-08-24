# CLI reference

Every verb takes the plan directory as its first argument. Expected errors
print as one line and exit `2`; `check` exits `1` on findings it fails.

## `kumihimo new PATH [--name NAME]`

Scaffold a plan: `kumihimo.yaml` with the engineering pack, `nodes/`, and a
starter node to delete once it has company. Refuses an existing plan.

## `kumihimo add PLAN ID [options]`

Create a node. `--kind` (default `task`), `--title`, `--body`, `--needs ID`
(repeatable or comma-separated), `--in ID`, `--field key=value` (repeatable;
values are coerced through the kind's field specs — ints, bools, comma-lists).
Every edge target must already exist; ids are lowercase slugs
(`[a-z0-9-]`, `/` for namespaces).

## `kumihimo set PLAN ID [options]`

Update a node: `--title`, `--kind`, `--body`, `--priority`, `--field
key=value`, `--unset key`. Hand-written comments in the file's frontmatter
survive.

## `kumihimo link PLAN SRC (--needs|--in|--to) TARGET [--rel REL]`

Draw exactly one edge. `--needs` is refused (with the path) when it would
close a cycle; `--to`/`--rel` draws an annotation.

## `kumihimo check PLAN [--strict]`

Validate: cycles with their paths, dangling edges, unknown kinds, field
breaches, orphans, dependencies on still-open nodes, empty bodies. Errors
exit `1`; `--strict` makes warnings fail too.

## `kumihimo braid PLAN [options]`

Compile. `-o FILE` writes instead of stdout (stdout is exact UTF-8 bytes —
pipe it anywhere). `--strategy linear|grouped`, `--where key=value`
(repeatable, matches effective fields; list fields match by containment),
`--from ID` (the node and everything after it), `--until ID` (the node and
everything it needs), `--in ID` (one group's members), `--dry` (order only),
`--diagram/--no-diagram`.

## `kumihimo export PLAN [--format mermaid|dot] [-o FILE]`

The graph as diagram source. GitHub renders Mermaid natively.

## `kumihimo edit PLAN [--port N] [--open/--no-open]`

Serve the live canvas on `127.0.0.1` (only). See [the editor](../howto/editor.md).

## `kumihimo mcp PLAN`

Serve the plan over MCP stdio. See [Claude over MCP](../howto/claude-mcp.md).
