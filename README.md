# Kumihimo

**組紐 — many threads in, one cord out.**

Kumihimo is the Japanese craft of braiding many separate threads into a single
cord. This tool works the same way: you lay out a plan as a **graph of
plain-text files**, and Kumihimo *braids* that graph into a single,
well-ordered **prompt** an LLM or coding agent can act on.

Two things it does:

1. **Visualize a plan as a graph.** Nodes and edges you can see, arrange, and
   reason about — backed by Markdown files that live in git and diff cleanly.
2. **Pull a prompt from the graph.** Walk the dependencies and compile one
   deterministic, well-ordered prompt.

The files are the only source of truth. The visual editor, the CLI, and the
MCP server (so Claude can restructure your plan for you) are all thin clients
over the same operations.

## Status

**Pre-alpha — v0.1 is being built in the open.** The design is
[PLAN.md](PLAN.md); progress lives in [build/state/queue.md](build/state/queue.md).
Nothing below works yet unless the queue says its milestone is done.

What v0.1 will look like:

```
pip install kumihimo
kumihimo new myplan          # scaffold a plan (engineering starter kinds)
kumihimo edit myplan         # browser editor — arrange, add, link
kumihimo braid myplan        # one compiled prompt on stdout
```

A plan is a folder — one Markdown file per node, frontmatter for the graph:

```markdown
---
kind: task
title: Rate-limit middleware
needs: [api-endpoints, pick-algorithm]
effort: M
---
Middleware on every authenticated route. Fail open on Redis errors —
availability beats enforcement.
```

## Development

```
uv sync
uv run pytest -q
uv run python tools/lint.py
```

Conventions (enforced in CI): [CONVENTIONS.md](CONVENTIONS.md). Contributions:
[CONTRIBUTING.md](CONTRIBUTING.md).

## License

[MIT](LICENSE)
