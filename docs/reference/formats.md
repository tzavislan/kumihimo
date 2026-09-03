# File formats

A plan is a directory whose root holds `kumihimo.yaml`. Format version `1`.

```
myplan/
  kumihimo.yaml        # manifest: meta, kinds, compile defaults
  view.yaml            # layout sidecar (canvas-maintained, optional)
  .gitignore           # ignores .kumihimo/ (scaffold writes this)
  .kumihimo/
    events.jsonl        # advisory mutation log (canvas-maintained, optional)
  nodes/
    api-endpoints.md
    auth/login-flow.md # subfolders namespace ids: "auth/login-flow"
```

## Node files

YAML frontmatter between `---` lines, then the body — plain Markdown prose,
preserved byte-for-byte by every tool operation.

```markdown
---
kind: task
title: Rate-limit middleware
needs: [api-endpoints, pick-algorithm]
in: [ship-guarded-api]
effort: M
acceptance:
  - 429 + Retry-After on breach
links:
  - {to: redis-outage, rel: threatened-by}
---
Middleware on every authenticated route. Fail *open* on Redis errors.
```

Reserved keys: `kind`, `title` (optional — defaults from the id), `needs`,
`in`, `links` (strings or `{to, rel}` maps), `agents`, `skills`, `trains`
(mention edges — see below), `priority` (int, breaks ordering ties). Every
other key is a field for the kind to validate. Scalars coerce where obvious
(`needs: api` means `[api]`).

Ids come from filenames: lowercase `[a-z0-9-]`, `/` for namespaces — enforced
so plans survive case-insensitive filesystems.

## Mentions: agents, skills, trains

Three more reserved keys, parsed exactly like `needs`/`in` (scalar-or-list,
salvaged to empty on the wrong type). They are *mention edges* — recorded and
kind-checked, but never consulted by the topological sort or the cycle guard:

```yaml
---
kind: task
title: Rate-limit middleware
needs: [api-endpoints]
agents: [claude-fable-5]      # each target must be kind: agent
skills: [kumihimo-iteration]  # each target must be kind: skill
trains: [kumihimo-retro]      # each target must be kind: agent or skill
---
```

`check` treats a dangling mention target as an error, the same as a dangling
`needs`/`in`/`links` target, and — once the target exists and its own kind
resolves — additionally checks that the target's *kind* matches the key: an
`agents:` target that isn't kind `agent`, a `skills:` target that isn't kind
`skill`, or a `trains:` target that's neither `agent` nor `skill`, is also an
error. A mention edge counts as a connection for the orphan rule, the same as
any other edge.

### Braid rendering

A task with mentions gets *Assigned:* (agents), *With:*
(skills), and *Trains:* (trains) lines, each rendering only when that key is
non-empty — a plain task with no crew gets none of them. Each cites its
targets as `Title (id)`: unlike a `needs` dependency, a mentioned agent or
skill is not guaranteed a number in the document (the grouped strategy's Cast
section, below, pulls agent/skill nodes out of the numbered flow entirely, and
a `--for` slice may not select the mentioned node at all), so the id is the
one handle that always resolves. See [the CLI reference](cli.md) for `braid
--for` and `kumihimo crew`.

### Consult-links

A `links:` entry with `rel: consult` whose target is kind `reference` renders
as its own line instead of folding into the generic See-also list:

```
*Consult:* Ward postmortem — docs/postmortems/ward.md (via recall query ward --corpus v1)
```

`(via <retriever>)` is omitted when the reference's `retriever` field is
empty. A `rel: consult` link to a non-reference target is not a consult-link
and renders exactly as any other link always has.

### The Cast section

The grouped strategy (only) gets its own **Cast** section, right after the
"how to read this braid" rubric and before the first work section — briefing
the crew before the work, the same reason a `preamble` goes before the plan.
Cast introduces every crew member the braid's text actually *cites*: agent/
skill nodes that are themselves selected, plus any agent/skill any selected
node's `agents:`/`skills:`/`trains:` names even when that crew member isn't
itself selected (a `--where` filter can drop an agent from the selection —
agent kind carries no `status` field — while the tasks that name it stay
selected and keep citing it by title), plus `--for`'s own agent always. Each
entry lists its title and kind, then whichever of its informative fields are
actually set — agent: `runtime`, `model`, `entry`, `trained`; skill:
`invocation`, `source`, `cadence`, `trained` — no empty placeholders. Cast
members are never numbered and never appear a second time among the ordinary
items (only when they are themselves selected — a cited-but-unselected crew
member was never going to be numbered either way); the linear strategy has no
Cast section, so a plan compiled `--strategy linear` renders its agent/skill
nodes as ordinary items instead.

### `braid --for <agent-id>`

Compiles one agent's work orders: every node whose `agents:`/`skills:`/
`trains:` mentions that agent, the skill nodes those mentioned tasks in turn
mention, and the agent's own node. Deliberately *not* whatever the agent
node's own `needs:`/`in:`/`links:`/mentions point at — those are not part of
the selection, and degrade through the usual stub mechanism (a `needs` target
still outside the selection becomes a stub, same as for any other slice) or
simply don't appear, exactly like an out-of-selection dependency anywhere
else in the braid. `--where`/`--from`/`--until`/`--in` still narrow the
result the same way they always compose. An id that exists but isn't kind
`agent` is a `KumihimoError` naming the kind it actually is. When the agent
node carries a `retrieval` field, the compiled text opens with it right after
the top header:

```
# Braid: API Guard
*Ground with:* grep the repo for the symbol first, then check docs/
```

silently omitted when the agent has no `retrieval`.

### `kumihimo crew` / the `crew` MCP tool

Lists every agent/skill/reference node, sorted by kind then id, with its
informative fields, its `trained` date, and mention counts — how many nodes
reference it via each of `agents:`/`skills:`/`trains:`, plus (for references)
its consult-link count. Dates print exactly as written and are never compared
to the clock: this library has none (PLAN2 §3.6). Deciding a skill is
overdue for retraining is the reader's judgment on `crew`'s output, not
something `check` enforces.

### `kumihimo export --format jsonl`

One JSON object per line, sorted by node id: `id`, `kind`, `title`, `body`,
`effective` (the node's fields with kind defaults filled in), and `edges`
(`needs`, `in`, `links: [{to, rel}]`, `agents`, `skills`, `trains`). Compact
separators and `ensure_ascii` are pinned so the same plan exports the same
bytes on every OS; the file ends with exactly one trailing newline. This is
the RAG ingestion shape (PLAN2 §3.7): any indexer reads it offline, and the
library itself never fetches or embeds anything. `jsonl` gates on check
errors, the same refusal `braid` gives; `mermaid`/`dot` do not — see
[the CLI reference](cli.md) for why.

Shipped in the engineering pack alongside `task`/`milestone`/`decision`/
`risk`/`question` are the three kinds mentions typically point at. No field on
any of them is required — a bare `kind: agent` node still loads and checks
clean. `trained` is a `str` field: write it as `trained: "2026-08-24"`, quoted
— an unquoted `2026-08-24` parses as a YAML date, and `check` correctly
rejects it as a type error rather than silently coercing it.

**`agent`**

| Field | Type | Notes |
|---|---|---|
| `runtime` | choice | `claude-code`, `cloud`, `human`, `other` |
| `model` | str | e.g. `claude-fable-5` |
| `entry` | str | how it's invoked |
| `scope` | list | what it may touch |
| `retrieval` | str | its standing grounding command |
| `trained` | str | date it was last trained or tuned |

**`skill`**

| Field | Type | Notes |
|---|---|---|
| `invocation` | str | e.g. `/kumihimo-iteration` |
| `source` | str | path or URL to its definition |
| `cadence` | str | prose, e.g. "milestone close or 10 iterations" |
| `trained` | str | date it was last retrained |

**`reference`**

| Field | Type | Notes |
|---|---|---|
| `locator` | str | path, URL, or corpus name |
| `retriever` | str | the command that fetches it |

### `@id` prose mentions — read-only

A body may write `@id` to mention a node in prose ("hand this to
@claude-fable-5, who runs @kumihimo-iteration"). `check` scans for these and
warns when one dangles: `body mentions '@x' but no node 'x' exists`. That is
the entire effect — **bodies are never rewritten**; the scanner only reads
them. A prose mention is not itself a graph edge: it doesn't rescue an
otherwise-orphaned node the way `agents:`/`skills:`/`trains:` do — prose is
analysis-read, not structure.

The scanner is one documented regex: `@` followed by an id-shaped token
(`[a-z0-9][a-z0-9-]*(?:/[a-z0-9-]+)*`), matched only where it opens a line or
follows a whitespace character. That boundary keeps a mid-word `@` — an email
address typed into prose — from matching, but it is not a Markdown parser: an
`@token` that happens to open a line inside a fenced code sample (a Python
decorator, say) is indistinguishable from a real mention and will still be
scanned. That imprecision is accepted and documented, not fixed — see
`MENTION_RE` in `kumihimo/core/validate.py`.

## `kumihimo.yaml`

```yaml
format: 1
plan: API Guard
description: One paragraph of what this plan is.
kinds:
  from: engineering        # optional pack; omit to define everything here
  task:                    # extend or define kinds
    fields:
      component: {type: str}
    # template: inline Jinja2 or a path under the plan root
compile:
  strategy: grouped        # or linear
  preamble: |
    Prepended to every braid.
  epilogue: |
    Appended to every braid.
  diagram: true            # embed the Mermaid overview
  # cord: my-cord.j2       # replace the whole document wrapper
```

Field spec keys: `type` (`str` | `int` | `bool` | `list` | `choice`),
`options` (for choice), `required`, `default`.

## `view.yaml`

```yaml
layout:
  api-endpoints: {x: 40, y: 200}
collapsed: [ship-guarded-api]
```

`layout`: integers, sorted keys, flow-style — a layout shuffle is a
two-line diff. `collapsed`: which container ids (PLAN2.md §2.3 lens 1 — any
node named in another node's `in`) are currently folded to a chip on the
canvas; sorted, flow-style, and the key is dropped entirely rather than
persisted empty. Semantics never live here; deleting the file costs you an
arrangement and which containers were folded, nothing more.

## `.kumihimo/events.jsonl`

An advisory log of recent mutations, one JSON object per line, created on
demand by the first op that runs against the plan:

```json
{"actor": "cli", "op": "add_node", "targets": ["b"]}
{"actor": "mcp", "op": "update_node", "targets": ["rate-limit-core"]}
```

`actor` is set by the thin client that ran the op — `"cli"`, `"mcp"`, or
`"editor"` (the running canvas's own HTTP ops API) — and defaults to `"api"`
for a raw library call with none of those in front of it. `op` is the
mutation's name (`add_node`, `update_node`, `link`, `unlink`, `rename_node`,
`remove_node`); `targets` is every node id a fresh payload digest diff would
see change — for `rename_node`, the old id, the new id, and every referrer
whose file got rewritten; for `remove_node` with `force`, the removed id plus
every referrer stripped. **No timestamp, ever** — this library has no clock
(PLAN2 §3.6, the same guarantee `crew`'s `trained` dates rely on); the
running editor correlates purely by tailing the file from its own last-seen
byte offset, which is all its attribution toasts need. The log grows to 400
lines before it's truncated back down to the newest 200 (oldest dropped
first) — hysteresis, not a tight cap at 200: truncating on every single
append once past a tight cap forced the editor's tailer to replay the whole
log far more often than truncation itself actually needed to run. Best-
effort throughout: a write that fails (a read-only mount, a locked file) is
silently skipped rather than failing the op it's attached to, and two
writers appending at nearly the same moment can race, with one's line lost
to the other's — acceptable for an advisory log, unlike a node file.
`.kumihimo/`'s mere presence, with any
content, never changes what `check` or `braid` compute — the store's load
path only ever reads `nodes/**/*.md`. Gitignored by `kumihimo new`'s own
`.gitignore`; see [the editor guide](../howto/editor.md#motion-and-attribution)
for how this log becomes attributed toasts and pulses on the canvas.

## Fidelity guarantees

Untouched files are never rewritten. Written files keep frontmatter comments,
key order, quoting, newline style (LF/CRLF), and BOM; bodies are verbatim.
One documented normalization: block-sequence indentation in a file an
operation actually edited settles to the canonical two-space-dash style.
