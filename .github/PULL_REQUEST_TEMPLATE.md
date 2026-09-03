Thanks! Two things keep reviews fast here:

- [ ] The battery passes locally, in CI's order:
  `uv run ruff check . && uv run ruff format --check . && uv run mypy && uv run pytest -q && uv run python tools/lint.py`
  (plus `npm run typecheck && npm run build` in `frontend/` if you touched it)
- [ ] [CONVENTIONS.md](../CONVENTIONS.md) holds: tagged headers, files under
  the cap, docs updated in the same commit as behavior changes.

**What this changes and why:**
