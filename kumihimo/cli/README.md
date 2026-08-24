# cli — the terminal client

<!-- BEGIN GENERATED INDEX -- do not edit by hand -->
| file | purpose |
|---|---|
| `__init__.py` | The command-line client: one module per verb, assembled in app.py. Thin over core.ops and compile — no logic of its own. |
| `app.py` | Assembles the Typer application and provides the console entry point; owns only --version and help, with each verb registered from its own module as milestones… |
<!-- END GENERATED INDEX -->

## What this is

`kumihimo` in a shell. `app.py` assembles the Typer app and owns `--version`;
each verb (`new`, `add`, `link`, `check`, `braid`, `export`, `edit`, `mcp`)
gets its own module as its milestone lands. Verbs call `core.ops` and
`compile` — anything smarter than argument parsing and output formatting is in
the wrong layer if it's here.
