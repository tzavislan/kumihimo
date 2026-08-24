# tests — the deterministic spine's coverage

<!-- BEGIN GENERATED INDEX -- do not edit by hand -->
| file | purpose |
|---|---|
| `test_boundaries.py` | Enforces PLAN.md §7.1 invariant 3: core/ and compile/ import no client-layer or UI/server/template library code. The boundary is a test, not a good intention (… |
| `test_cli.py` | The installed command behaves at the surface: --version prints the package version, and a bare invocation shows help without erroring. |
| `test_lint.py` | Behaviour coverage for every conventions-linter check: the cap and its counting rules, the @exempt grammar, header tags, public @purpose, and README index gene… |
<!-- END GENERATED INDEX -->

## What this is

Behaviour-first tests per PLAN.md §7.3: nearly everything in Kumihimo is
deterministic (parsing, ordering, round-trip, rendering), so nearly everything
gets unit or golden coverage, and architectural rules (import boundaries,
conventions) are enforced by tests rather than good intentions. The one thing a
green run here never claims is that a braided prompt steers an agent well —
that verification is manual, on real runs, or it is reported "not verified".

Test files carry the `@file`/`@purpose` header like all code; individual test
functions are exempt from the per-item `@purpose` rule.
