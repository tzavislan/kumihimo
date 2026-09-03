# MCP tools

`kumihimo mcp <plan>` serves one plan; every tool signature is therefore free
of path arguments. Errors carry the same messages the CLI prints.

| Tool | What it does |
|---|---|
| `get_plan` | The whole graph: manifest meta plus every node's identity, edges (`needs`/`in`/`links`), mentions (`agents`/`skills`/`trains`), and fields (bodies elided) |
| `get_node(node_id)` | One node in full: raw and effective fields, edges, mentions, body |
| `add_node(node_id, kind, title?, body?, fields?, needs?, in_?)` | Create a node; edge targets must exist |
| `update_node(node_id, kind?, title?, body?, priority?, set_fields?, unset_fields?)` | Change a node; file comments survive |
| `remove_node(node_id, force?)` | Delete; refuses while referenced (naming referrers) unless `force` strips the edges too |
| `link(src, needs?/in_?/to?/agents?/skills?/trains?, rel?)` | Draw exactly one edge from the six; cycle-closing `needs` is refused with the path, and a wrong-kind mention target (`agents` wants `agent`, `skills` wants `skill`, `trains` wants `agent` or `skill`) is refused naming the kind it expected |
| `unlink(src, needs?/in_?/to?/agents?/skills?/trains?)` | Remove exactly one edge, mentions included; absent edges error |
| `rename_node(old, new)` | Move to a new id; file bytes untouched, every referrer and the view layout fixed |
| `check()` | Every validation finding, errors first |
| `braid(strategy?, where?, from_?, until?, in_?, for_agent?, diagram?, dry?)` | Compile; returns `{text, order, warnings}`. `for_agent` is `--for`: one agent's work orders, opening with `*Ground with:*` when it has a `retrieval` field. A `for_agent` that doesn't exist or isn't kind `agent` raises, naming which |
| `ready(for_agent?)` | Nodes whose own status is `todo` and whose dependencies are all satisfied (no status, or `done`/`settled`/`answered`). `for_agent` narrows to nodes whose `agents:` key names that id — `skills:`/`trains:` are deliberately not consulted. Validated the same way as `braid`'s `for_agent`: raises rather than returning an empty list for a bad id |
| `crew()` | Every `agent`/`skill`/`reference` node, sorted by kind then id: effective fields, `trained` date verbatim, mention counts (per mention key, plus consult-links for references) |

Mutations write to disk immediately — files are the only truth — so a running
`kumihimo edit` canvas follows every MCP change live.

`trained`/`cadence` values from `crew()` are never compared to a clock — no
surface in this library decides staleness; the caller reading `crew()`'s
output does (PLAN2 §3.6).
