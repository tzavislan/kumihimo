# CLAUDE.md — Kumihimo

Agent context for this repository. Read this, then [PLAN2.md](PLAN2.md) —
the v0.2 design authority (approved 2026-08-24; [PLAN.md](PLAN.md) is the
v0.1 record). Deviations from the plan are recorded in
[build/state/journal.md](build/state/journal.md), never silently.

**Running the project?**
[`/kumihimo-manage`](.claude/skills/kumihimo-manage/SKILL.md) is the umbrella
— status, queue grooming, milestone close, release prep — and carries the
Training log. The work queue is [build/state/queue.md](build/state/queue.md),
one build pass is
[`/kumihimo-iteration`](.claude/skills/kumihimo-iteration/SKILL.md), and
lessons fold back into all three skills via
[`/kumihimo-retro`](.claude/skills/kumihimo-retro/SKILL.md) at each milestone
close.

## Invariants — do not violate

1. **Everything goes through `core.ops`.** CLI, HTTP, and MCP are thin clients.
   If a mutation path bypasses the ops layer, it is a bug even when it works.
2. **Files are the only truth.** An op succeeds when the bytes are on disk.
   The editor holds no unsaved semantic state; git is the undo.
3. **`core/` and `compile/` import no client code** — enforced by
   `tests/test_boundaries.py`.
4. **Deterministic braid.** Same plan → byte-identical prompt, on every OS.
   Golden tests guard it; nondeterminism is a bug where it becomes observable.
5. **No network, no LLM calls, no telemetry in the library.** Ever.
6. **`format: 1` is versioned.** Format changes ship with a migration command.
7. **Round-trip fidelity is data integrity.** A node file the user wrote must
   survive load→save byte-for-byte unless the operation *is* an edit to it.
   "Kumihimo reformatted my file" is treated as data loss.

## Rules of the repo

- **Git stays current: push at every milestone close** (standing say-so,
  Thomas 2026-08-24) — the public repo reflects each upgrade. Off-cycle
  pushes still need his explicit yes; never push mid-iteration. A red CI
  after a push is the top of the queue until green.
- **Documentation ships with the change, not after** (Thomas, 2026-08-24).
  An item that changes user-visible behavior updates its docs-site page in
  the same commit; UI-pixel changes re-shoot screenshots
  (`tools/screenshots.py`) at milestone close; changed README commands get
  re-verified on a clean checkout. CI's strict docs build gates the rest.
- **Never publish to PyPI** — release is Thomas's act, via the tagged release
  workflow.
- Coding rules are [CONVENTIONS.md](CONVENTIONS.md) and they are enforced:
  `uv run python tools/lint.py` (add `--fix` to regenerate README indexes).
- Full local check, in CI's order:
  `uv run ruff check . ; uv run ruff format --check . ; uv run mypy ; uv run pytest -q ; uv run python tools/lint.py`
- Prompt-effectiveness claims follow the verification bar in CONVENTIONS.md —
  say **"not verified"** unless a braid was actually run against a real agent.

## Layout

`kumihimo/core` model+store+ops · `kumihimo/compile` the braid ·
`kumihimo/cli|server|mcp` thin clients · `frontend/` TS editor source (M4) ·
`tools/` conventions linter · `tests/` spine coverage ·
`examples/` worked plans · `plans/roadmap/` Kumihimo's own plan (from M2) ·
`docs/` mkdocs site (M6). Milestones and scope: PLAN.md §9.
