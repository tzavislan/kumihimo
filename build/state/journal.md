# Build journal

One entry per iteration, newest at the bottom. The queue is the state; this is
the memory. Retros read from the last `retro:` marker forward.

---

## Iteration 1 — 2026-08-23 — K0: M0 bootstrap

**What now exists:** git repo (main), MIT license, pyproject (hatchling,
Python ≥3.11, uv-managed 3.12), package skeleton (`core/`, `compile/`,
`server/`, `mcp/`, `cli/`) with tagged headers and folder READMEs,
`kumihimo --version` working, `tools/lint.py` enforcing the cap/tags/README
indexes/@exempt grammar with 15 behaviour tests, import-boundary test
(relative-import-proof), CLI smoke tests, CI workflow (ubuntu+windows),
CLAUDE.md, CONVENTIONS.md, CONTRIBUTING.md, CHANGELOG.md, both skills, this
state.

**Verified:** ruff check, ruff format --check, mypy strict (8 files), pytest
17/17, `tools/lint.py` clean — all run locally on Windows. CI itself **not
verified** (no remote yet; first push will show it).

**Lessons already banked:**
- The linter flagged its *own* header because prose mentioned "@exempt" —
  declarations must start their line; the grammar now says so. Self-hosting
  the rules caught this in the first hour; that is the point of them.
- Click 8.2 exits 2 (not 0) on bare-invocation help. Test asserts the
  contract (help text, no traceback), not the fragile code.

**Deviations from PLAN.md:** none yet. Kind-pack data will live at
`kumihimo/packs/` rather than `kumihimo/compile/packs/` so `core` can load
kind schemas without importing `compile` (boundary integrity) — noted ahead
of K1, where it lands.

## Iteration 2 — 2026-08-23 — K1: model types and kind system

**What now exists:** `core/errors.py` (KumihimoError, CycleError carrying its
path), `core/model.py` (Node with needs/in/links/priority/fields, Finding,
FieldSpec, KindDef, CompileSettings, Manifest, slug regex, default_title),
`core/kinds.py` (pack loading via importlib.resources, resolve_kinds merging
pack + manifest overrides with findings-not-crashes, per-type field
validation, effective_fields defaults), `packs/engineering/kinds.yaml` (five
kinds per PLAN §3.2). The planned deviation above is now real: packs live at
`kumihimo/packs/`.

**Verified:** 12 new tests (29 total), mypy strict, ruff, conventions linter —
all green locally.
