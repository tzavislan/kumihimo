# Contributing

Thanks for looking. Kumihimo is early — the design authority is
[PLAN.md](PLAN.md), and the fastest way to help is to read it first.

## Setup

[uv](https://docs.astral.sh/uv/) manages everything, including the Python
version:

```
uv sync
```

## Before a PR

Run what CI runs:

```
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest -q
uv run python tools/lint.py
```

`tools/lint.py --fix` regenerates folder-README indexes when they're stale.

## House rules

[CONVENTIONS.md](CONVENTIONS.md) is short and enforced: the `@file`/`@purpose`
docstring tag scheme, a 600-code-line file cap, a README in every code folder,
and hard architectural boundaries (`core/` imports no client code — a test
will fail if you try). PRs that change behaviour show the behaviour change,
not just green tests; changes to braid output update the golden files and the
diff is part of the review.

The frontend (`frontend/`, from M4) is TypeScript and follows the same tag
scheme in `/** */` blocks; end users never need Node — CI builds the assets
into the wheel.

## Scope guard

v0.1's non-goals are listed in PLAN.md §1 — no execution engine, no LLM calls
inside the library, no cycles/conditionals. PRs adding those will be declined
kindly and pointed at the plan; open an issue first if you think the plan is
wrong, that's fair game.
