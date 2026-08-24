# Conventions

These exist so the codebase stays navigable by both people and coding agents,
and so no single file becomes a black box. They are carried over from
Yorishiro/Whetstone, and the hardest-won lesson comes with them: **rules
nobody enforces rot.** Every rule below is enforced by `tools/lint.py` in CI,
or by a test, from the first commit.

## Documentation tags

Every **file**, every **public function**, and every **core method** carries a
docstring using this scheme:

```python
"""
@file        kumihimo/core/graph.py
@purpose     Deterministic ordering over the plan DAG, so the same plan always
             braids to byte-identical output.
@layer       core
@tags        topo-sort, determinism, cycles
@related     kumihimo/core/validate.py (reports the cycles this detects),
             kumihimo/compile/braid.py (consumes the order)
@design      PLAN.md §4.1
"""
```

```python
def braid_order(plan: Plan) -> list[Node]:
    """Return every node in deterministic topological order.

    @purpose  The one ordering the whole system trusts; ties broken by
              (priority desc, id asc), never by dict order or OS.
    @tags     topo-sort, determinism
    @related  Plan.braid (consumes this)
    """
```

| Tag | Means |
|---|---|
| `@purpose` | What it does and why, in plain terms. Behaviour, not construction. |
| `@layer` | Where it sits (core, compile, server, mcp, cli, tools, tests). |
| `@tags` | Lowercase, hyphenated, searchable concepts — `grep "@tags.*topo"` finds every relevant spot. |
| `@related` | Paths a reader needs next, each with a word on why. |
| `@design` | The PLAN.md or docs section explaining the reasoning. |

The first line of a function docstring stays a normal one-line summary so IDE
hovers behave. Public functions get at least `@purpose`; anything on a public
interface gets the full set. **Enforced:** a missing `@file`/`@purpose` header,
an `@file` that doesn't match the real path, or a public item without
`@purpose` fails `tools/lint.py`. Test files carry the file header; individual
test functions are exempt from the per-item rule.

The same fields apply to the TypeScript frontend in `/** */` blocks (linted
from M4).

## Design

- **One responsibility per type, one concept per file.** If a file's purpose
  needs the word "and", split it.
- **Everything goes through `core.ops`.** CLI, HTTP, and MCP are thin clients;
  no mutation path bypasses the ops layer.
- **`core/` and `compile/` import no client or UI code** — no typer, rich,
  fastapi, mcp, watchfiles; core also imports no jinja2 and no `compile`.
  Enforced by `tests/test_boundaries.py`, including against relative-import
  dodges.
- **Files are the only truth.** An operation succeeds when the bytes are on
  disk. No in-memory state worth losing, no caches that can lie.
- **Determinism is an invariant.** Same plan in, byte-identical braid out —
  golden tests guard it. Anything nondeterministic (dict iteration order, OS
  path order) is a bug at the point it becomes observable.

## File size

**600 lines per file, excluding comments, blank lines, and docstrings** —
thorough documentation never fights the cap. Approaching it, split by
responsibility into a folder with its own README. Exemptions are explicit and
rare:

```text
@exempt file-size reviewer=<name> reason=<free text to end of line>
```

placed in the file's header docstring. The linter reports every exemption in
every run (and flags ones whose file has shrunk back under the cap), so they
cannot accumulate quietly.

## Folders

**Every folder with Python files contains a `README.md`**: a generated index
(from the files' own `@purpose` lines — `tools/lint.py --fix` refreshes it,
and CI fails when it's stale) above hand-written prose. `--fix` never creates
a missing README: the prose half is human or it is nothing.

## Comments in code

Explain **why**, not what. A comment restating the line above it is noise; a
comment recording the incident a defensive branch exists because of is the
most valuable thing in the file.

## Verification

A compile is not a verification and a green suite is not a verification of
behaviour. The deterministic spine gets real tests; claims about *prompt
effectiveness* — whether a braid steers an agent well — require running the
braid against a real agent and reading the result. Reports say **"not
verified"** when that has not happened.

One more testing rule, learned when dogfood state moved under a test: **tests
pin invariants, not living state.** The roadmap plan's statuses change as
work completes; a test asserting "mcp-tools is ready" breaks the moment the
project makes progress. Pin what must always hold.
