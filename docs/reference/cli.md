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
everything it needs), `--in ID` (one group's members), `--for AGENT-ID` (one
agent's work orders: nodes that mention it, the skills those tasks in turn
mention, and the agent itself — anything else the agent's own edges point at
is not part of the selection and degrades through the normal stub machinery
like any out-of-selection dependency; opens with *Ground with:* when the
agent has a `retrieval` field; an id that isn't kind `agent` errors naming
the kind it is), `--dry` (order only), `--diagram/--no-diagram`. See
[mentions and the crew surface](formats.md#braid-rendering) for what
`--for` and the grouped strategy's Cast section render.

## `kumihimo crew PLAN`

List every `agent`/`skill`/`reference` node as a table: kind, id, title, its
informative fields, its `trained` date (printed verbatim — nothing here
compares it to a clock), and mention counts. See
[the crew surface](formats.md#kumihimo-crew-the-crew-mcp-tool).

## `kumihimo export PLAN [--format mermaid|dot|jsonl] [-o FILE]`

The graph as diagram source (`mermaid`, GitHub-native, or `dot`) or as
JSON Lines (`jsonl`, one object per node — see
[the jsonl shape](formats.md#kumihimo-export-format-jsonl)), the offline
retrieval-indexing feed (PLAN2 §3.7). Machine-feed formats gate on check
errors; diagnostic formats do not: `jsonl` refuses (exit `2`, `braid`'s own
message) when the plan has check errors, because a downstream indexer trusts
it the way an agent trusts a braid; `mermaid`/`dot` render regardless of
errors, because seeing a broken plan drawn is exactly when a picture earns
its keep.

## `kumihimo edit PLAN [--port N] [--open/--no-open]`

Serve the live canvas on `127.0.0.1` (only). See [the editor](../howto/editor.md).

## `kumihimo mcp PLAN`

Serve the plan over MCP stdio. See [Claude over MCP](../howto/claude-mcp.md).
