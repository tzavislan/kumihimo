# Concepts

## The graph model

A plan is a directory. Each node is one Markdown file: YAML frontmatter for
structure, prose body for meaning. The core understands exactly six things
about a node:

| Thing | Where | What it does |
|---|---|---|
| **identity** | the filename (`nodes/rate-limit-core.md` → id `rate-limit-core`) | stable reference; rename fixes every referrer |
| **prose** | `title:` + the body | placed, never interpreted |
| **order** | `needs: [a, b]` | the only edge the compiler sequences by |
| **membership** | `in: [milestone]` | the only edge the grouped strategy sections by |
| **annotation** | `links: [{to: x, rel: informs}]` | drawn and cross-referenced, zero compiler semantics |
| **mention** | `agents:` / `skills:` / `trains:` | who's assigned, what skill, who trains — checked to exist and be the right kind, never ordered |

Everything else on a node — `status`, `effort`, `confidence`, whatever your
domain needs — is a **field**, validated by the node's *kind* but invisible to
the core. That line is deliberate: the compiler always has structure to grip
(order and membership are core), while node *meaning* stays entirely yours.

Mentions carry no ordering — `check` confirms the target exists and is the
right kind (an `agents:` target must itself be a node of kind `agent`, and so
on), but the topological sort never looks at them. A body may also mention a
node in prose (`@id`); that's scanned read-only for dangling references and
the body is never rewritten, and — unlike the frontmatter mentions — a prose
mention alone doesn't rescue a node from the orphan rule.

Cycles are validation errors, named with their path. There is no execution
engine, no scheduler, and no LLM call anywhere in the library.

## Kinds

A kind declares fields (type, options, required, default) and optionally a
Jinja2 template that renders nodes of that kind into prompt text. Kinds come
from a shipped pack (`kinds: {from: engineering}` gives you `task`,
`milestone`, `decision`, `risk`, `question`) or straight from your manifest —
see [custom kinds](howto/custom-kinds.md). Packs are copied-in defaults, not
a type hierarchy.

## Files are the only truth

Every surface — CLI, editor, MCP — is a thin client over one operations
layer, and an operation succeeds when the bytes are on disk. The editor holds
no unsaved document: each gesture writes immediately, and the canvas re-renders
from what a file watcher reads back. Two consequences worth internalizing:

- **Fidelity.** Files Kumihimo didn't touch are never rewritten. Files it did
  touch keep your comments, key order, newline style, and BOM. "The tool
  reformatted my file" is treated as data loss.
- **Concurrency.** Edit in vim, in the canvas, and over MCP simultaneously;
  the filesystem is the bus. Editor saves carry a file digest, and a stale
  digest is rejected (409) instead of clobbering the other writer.

Layout is not semantics: node positions live in `view.yaml`, a sidecar the
canvas maintains, so arranging your graph never dirties a node file's diff.

## The braid

`braid = select → order → render → weave`.

1. **Select** — the whole graph or a slice: `--where status=todo` (any
   effective field), `--from x` / `--until x` (dependency cones), `--in m`
   (one group's members). Excluded direct dependencies become one-line stubs
   ("already in place") so the prompt never references a ghost.
2. **Order** — one deterministic topological order (ties: priority
   descending, then id). Same plan in, byte-identical prompt out — template
   changes show up as reviewable golden diffs.
3. **Render** — each node through its kind's template, sandboxed. Templates
   state structure in prose: every task carries an *After:* line naming its
   real prerequisites by number and title.
4. **Weave** — the cord: preamble → Mermaid overview → a how-to-read rubric →
   sections → epilogue. `linear` gives one numbered sequence; `grouped` (the
   engineering default) turns each membership target into a titled section,
   dependency-ordered, with ungrouped prerequisites leading.

A DAG usually has many valid orders, and the braid doesn't pretend otherwise:
the chosen order is total, but the *After* lines carry the true constraints,
adjacent-but-independent items are marked as such, and the embedded diagram
lets the consuming agent parallelize deliberately.
