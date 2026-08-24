# cli — the terminal client

<!-- BEGIN GENERATED INDEX -- do not edit by hand -->
| file | purpose |
|---|---|
| `__init__.py` | The command-line client: one module per verb, assembled in app.py. Thin over core.ops and compile — no logic of its own. |
| `add_cmd.py` | `kumihimo add` — create a node from flags, coercing --field values through the kind's field specs (ints, bools, comma-lists) so typed fields are reachable from… |
| `app.py` | Assembles the Typer application and provides the console entry point; owns only --version and help, with each verb registered from its own module as milestones… |
| `check_cmd.py` | `kumihimo check` — render every finding as a table, summarize the plan, and exit 1 on errors (or on warnings too, under --strict). |
| `common.py` | What every verb shares: the stdout/stderr consoles and the one way to die — expected errors print as a styled message and exit 2, never as a traceback. |
| `link_cmd.py` | `kumihimo link` — draw one edge: --needs for dependency, --in for membership, --to/--rel for annotation. Cycle refusals surface with their path. |
| `new_cmd.py` | `kumihimo new` — scaffold a plan directory with the engineering pack and a starter node, then say what to do next. |
<!-- END GENERATED INDEX -->

## What this is

`kumihimo` in a shell. `app.py` assembles the Typer app and owns `--version`;
each verb (`new`, `add`, `link`, `check`, `braid`, `export`, `edit`, `mcp`)
gets its own module as its milestone lands. Verbs call `core.ops` and
`compile` — anything smarter than argument parsing and output formatting is in
the wrong layer if it's here.
