# tests — the deterministic spine's coverage

<!-- BEGIN GENERATED INDEX -- do not edit by hand -->
| file | purpose |
|---|---|
| `conftest.py` | Shared fixtures: a factory that lays a plan directory on disk from a dict of node files, so every test builds real plans the way users have them — as files. |
| `test_boundaries.py` | Enforces PLAN.md §7.1 invariant 3: core/ and compile/ import no client-layer or UI/server/template library code. The boundary is a test, not a good intention (… |
| `test_braid.py` | The pipeline behaves: selection filters and cones compose, stubs bridge cut edges, the check-error gate holds, both strategies produce their promised sections,… |
| `test_cli.py` | The installed command behaves at the surface: --version prints the package version, and a bare invocation shows help without erroring. |
| `test_cli_verbs.py` | The M1 demo path, end to end through the real CLI: new → add → link → check, plus field coercion, error exit codes, --strict, and the cycle named in check outp… |
| `test_example_apiguard.py` | Holds the shipped example to its promises: it validates clean, its braid order is deterministic and exactly what the graph implies, a hand-introduced cycle is … |
| `test_graph.py` | The ordering invariant, executable: braid_order is identical under any insertion order, priority then id breaks ties, cycles are named as exact paths (self-loo… |
| `test_kinds.py` | The kind system behaves: packs load, manifest overrides merge and extend, bad overrides become findings not crashes, field validation is precise per type, and … |
| `test_lint.py` | Behaviour coverage for every conventions-linter check: the cap and its counting rules, the @exempt grammar, header tags, public @purpose, and README index gene… |
| `test_ops.py` | The ops layer behaves: canonical files from add, comment-preserving updates, cycle-refusing links, tidy unlinks, renames that fix every referrer and the view l… |
| `test_store_roundtrip.py` | The fidelity contract, executable: untouched files are never written; touched files keep comments, key order, newline style, and BOM; bodies survive byte-for-b… |
| `test_validate.py` | Every check rule triggers on the file that breaks it and stays quiet on one that doesn't: kinds, fields, dangling edges, the cycle path, orphans, open dependen… |
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
