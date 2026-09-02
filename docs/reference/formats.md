# File formats

A plan is a directory whose root holds `kumihimo.yaml`. Format version `1`.

```
myplan/
  kumihimo.yaml        # manifest: meta, kinds, compile defaults
  view.yaml            # layout sidecar (canvas-maintained, optional)
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

Braid rendering — an *Assigned:*/*With:*/*Trains:* line per task, a Cast
section for crew nodes, `braid --for` — is not shipped yet; it arrives with
the crew surface work.

Shipped in the engineering pack alongside `task`/`milestone`/`decision`/
`risk`/`question` are the three kinds mentions typically point at. No field on
any of them is required — a bare `kind: agent` node still loads and checks
clean.

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

## Fidelity guarantees

Untouched files are never rewritten. Written files keep frontmatter comments,
key order, quoting, newline style (LF/CRLF), and BOM; bodies are verbatim.
One documented normalization: block-sequence indentation in a file an
operation actually edited settles to the canonical two-space-dash style.
