# MCP tools

`kumihimo mcp <plan>` serves one plan; every tool signature is therefore free
of path arguments. Errors carry the same messages the CLI prints.

| Tool | What it does |
|---|---|
| `get_plan` | The whole graph: manifest meta plus every node's identity, edges, fields, digest (bodies elided) |
| `get_node(node_id)` | One node in full: raw and effective fields, links, body |
| `add_node(node_id, kind, title?, body?, fields?, needs?, in_?)` | Create a node; edge targets must exist |
| `update_node(node_id, kind?, title?, body?, priority?, set_fields?, unset_fields?)` | Change a node; file comments survive |
| `remove_node(node_id, force?)` | Delete; refuses while referenced (naming referrers) unless `force` strips the edges too |
| `link(src, needs?/in_?/to?, rel?)` | Draw one edge; cycle-closing `needs` is refused with the path |
| `unlink(src, needs?/in_?/to?)` | Remove one edge; absent edges error |
| `rename_node(old, new)` | Move to a new id; file bytes untouched, every referrer and the view layout fixed |
| `check()` | Every validation finding, errors first |
| `braid(strategy?, where?, from_?, until?, in_?, diagram?, dry?)` | Compile; returns `{text, order, warnings}` |
| `ready()` | Nodes whose own status is `todo` and whose dependencies are all satisfied (no status, or `done`/`settled`/`answered`) |

Mutations write to disk immediately — files are the only truth — so a running
`kumihimo edit` canvas follows every MCP change live.
