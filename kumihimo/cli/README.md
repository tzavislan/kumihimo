# cli — the terminal client

<!-- BEGIN GENERATED INDEX -- do not edit by hand -->
| file | purpose |
|---|---|
| `__init__.py` | The command-line client: one module per verb, assembled in app.py. Thin over core.ops and compile — no logic of its own. |
| `add_cmd.py` | `kumihimo add` — create a node from flags, coercing --field values through the kind's field specs (ints, bools, comma-lists) so typed fields are reachable from… |
| `app.py` | Assembles the Typer application and provides the console entry point; owns only --version and help, with each verb registered from its own module as milestones… |
| `braid_cmd.py` | `kumihimo braid` — pull the cord: compile a plan (or a slice via --where/--from/--until/--in/--for) to stdout or a file, with --dry for the order alone. Output… |
| `check_cmd.py` | `kumihimo check` — render every finding as a table, summarize the plan, and exit 1 on errors (or on warnings too, under --strict). |
| `common.py` | What every verb shares: the stdout/stderr consoles and the one way to die — expected errors print as a styled message and exit 2, never as a traceback. |
| `crew_cmd.py` | `kumihimo crew` — list every agent/skill/reference node as a plain aligned table: its informative fields, its `trained` date (printed verbatim), and how many n… |
| `edit_cmd.py` | `kumihimo edit` — serve the plan's live canvas on localhost and open the browser. Read-only through M4; the write path is M5. |
| `export_cmd.py` | `kumihimo export` — the plan as a diagram source (Mermaid, GitHub-native, or Graphviz DOT) or as JSON Lines, the RAG ingestion shape (PLAN2 §3.7), to stdout or… |
| `link_cmd.py` | `kumihimo link` — draw one edge: --needs for dependency, --in for membership, --to/--rel for annotation. Cycle refusals surface with their path. |
| `mcp_cmd.py` | `kumihimo mcp` — serve one plan over MCP stdio so an agent can inspect, restructure, and braid it. Blocks until the client disconnects. |
| `new_cmd.py` | `kumihimo new` — scaffold a plan directory with the engineering pack and a starter node, then say what to do next. |
| `set_cmd.py` | `kumihimo set` — update a node from the shell: title, kind, body, priority, fields (coerced through the kind's specs), and unsets. The verb dogfooding found mi… |
<!-- END GENERATED INDEX -->

## What this is

`kumihimo` in a shell. `app.py` assembles the Typer app and owns `--version`;
each verb (`new`, `add`, `link`, `check`, `braid`, `export`, `edit`, `mcp`)
gets its own module as its milestone lands. Verbs call `core.ops` and
`compile` — anything smarter than argument parsing and output formatting is in
the wrong layer if it's here.
