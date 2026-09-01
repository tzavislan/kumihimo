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
`in`, `links` (strings or `{to, rel}` maps), `priority` (int, breaks ordering
ties). Every other key is a field for the kind to validate. Scalars coerce
where obvious (`needs: api` means `[api]`).

Ids come from filenames: lowercase `[a-z0-9-]`, `/` for namespaces — enforced
so plans survive case-insensitive filesystems.

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
