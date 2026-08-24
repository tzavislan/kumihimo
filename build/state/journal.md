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

## Iteration 3 — 2026-08-23 — K2: store with the fidelity contract

**What now exists:** `core/store.py` (find_root, frontmatter split with
verbatim bodies, tolerant normalization to Nodes with precise findings,
dirty-gated atomic saves, BOM/newline preservation, view.yaml helpers,
scaffold with starter node), `core/plan.py` (the Plan facade: load, nodes,
node, check placeholder, save), public API re-exported from `kumihimo`.

**Verified:** 15 round-trip tests including strict byte-equality on a CRLF
file after a field edit; 44 tests total, mypy strict, ruff, linter green.

**Lessons:**
- ruamel captures `\r` inside comment tokens — frontmatter must be normalized
  to LF before parsing, with the record's newline style applied only at write.
- Block-sequence indentation is an emitter setting, not round-trip-preserved:
  pinned to the canonical two-space-dash style. Fidelity bound documented:
  untouched files never re-serialize; *edited* files may normalize seq indent.
- Tool-transport gotcha: writing a literal U+FEFF into source is invisible and
  survives edits confusingly; store.py uses the escape, tests label the one
  deliberate literal.
- **Verification honesty failure, caught late:** the K2 commit chained checks
  as `cmd | tail -1 && next`, and the pipe made every check's exit code
  tail's 0 — ruff and mypy each had a live error when the commit claimed
  green. Never pipe a gating check; read exit codes unmasked. Candidate for
  the iteration skill at the M1 retro.

## Iteration 4 — 2026-08-23 — K3: deterministic graph ordering

**What now exists:** `core/graph.py` — braid_order (Kahn, sorted ready-heap,
priority-desc/id-asc ties, insertion-order-proof), find_cycle naming the exact
path deterministically (self-loops included), ancestor/descendant cones for
slicing. Dangling needs never block ordering; they are validation's finding.

**Verified:** 9 graph tests (53 total), mypy strict, ruff, exit codes read
unmasked this time.

## Iteration 5 — 2026-08-23 — K4: validation rules

**What now exists:** `core/validate.py` — per-node rules (missing/unknown
kind, field-schema breaches via kinds.validate_fields, dangling
needs/in/links naming edge kind and target, empty bodies) and whole-graph
rules (the cycle as one error with its path, orphans, dependencies on
still-open nodes via the generic status=="open" test), sorted errors-first
deterministically. `Plan.check()` wired through it; a clean two-node plan
checks to exactly [].

**Verified:** 10 validate tests (63 total), mypy strict, ruff, conventions
linter, exit codes unmasked.

## Iteration 6 — 2026-08-23 — K5: the ops layer

**What now exists:** `core/ops.py` — add_node (canonical frontmatter, strict
on ids/kinds/targets), update_node (permissive on field values, strict on
structure; comments survive), link/unlink (scalar-or-list aware; needs-links
refused with the path when they'd close a cycle), rename_node (file moved
bytes-untouched, every referrer spelling fixed, view.yaml layout followed),
remove_node (refuses while referenced, names referrers; force strips edges
and the view entry). Slug rule doubles as path-traversal protection —
tested: `../escape` and friends cannot reach ops.

**Verified:** 15 ops tests (78 total), whole battery green, exit codes read.

## Iteration 7 — 2026-08-23 — K6: CLI verbs

**What now exists:** `kumihimo new/add/link/check` — new scaffolds and says
what to do next; add coerces --field values through the kind's specs (ints,
bools, comma-lists) so typed fields work from a shell; link draws one edge
per call and surfaces cycle refusals with their path; check renders the
findings table with an exit code scripts can gate on (--strict makes
warnings fail). KumihimoErrors print as one styled line and exit 2 — never a
traceback.

**Verified:** 7 CLI integration tests including the full new→add→link→check
demo path (85 total), battery green and gated.

**Note for K5's earlier lesson:** second ungated-commit slip happened at K5
close (unused import; caught immediately). The && gate is now the committed
habit; both incidents go to the M1 retro together.

## Iteration 8 — 2026-08-23 — K7: API-Guard example — M1 complete

**What now exists:** `examples/apiguard/` — the PLAN.md §3.3 worked example
as a real plan: seven nodes across all five engineering kinds, a milestone
grouping four members, an annotation edge with a relation label, a layout
sidecar. Tests hold it to its promises: checks completely clean (zero
findings), braid order pinned exactly, a hand-introduced cycle is named
end-to-end through the CLI, and a field edit is exactly a one-line diff.

**Verified:** 4 integration tests (89 total), full gated battery.

**Deviation note:** PLAN.md's manifest example extends `task` with `effort`
for illustration; the shipped engineering pack grew `effort` natively at K1,
so the example manifest needs no override. PLAN.md stands as written (it is
the planning record); the docs at M6 will show a custom-field example with a
genuinely new field.

**M1 demo, run for real:** `uv run kumihimo check examples/apiguard` →
"7 node(s), 8 edge(s): 0 error(s), 0 warning(s)" (actual output; a first
draft of this entry said 10 edges from mental arithmetic instead of running
it — the verification bar exists for exactly that). Cycle demo and
one-line-diff demo run as tests. Prompt-effectiveness: n/a until M2 (no
braid yet) — nothing claimed.

## retro: 2 lessons through iteration 8 — M1 close

Read: iterations 1-8. Durable lessons folded:

1. **Gated verification** (incidents in iterations 3 and 6: piped exit codes,
   then printed-but-ungated codes; both committed errors under green-sounding
   reports) → kumihimo-iteration Step 5: never pipe a gating check; the
   commit sits at the end of the && chain; format applies before checks.
2. **Journal numbers come from executed commands** (iteration 8 edge-count
   fabricated by arithmetic, caught before commit) → kumihimo-iteration
   Step 6.

Considered, not folded: ruamel CRLF/indent behavior (lives in store.py
comments and round-trip tests, where the next reader needs it); the literal
U+FEFF transport gotcha (one-off, documented at the site). Nothing pruned —
the skills are eight iterations old.

loop.json: iteration=8, last_retro_iteration=8.

## Iteration 9 — 2026-08-23 — kumihimo-manage skill (Thomas, mid-session)

Thomas asked mid-session to "make sure there is a Kumihimo manage skill that
gets trained." Iteration + retro covered building and training but not the
management surface. Added `.claude/skills/kumihimo-manage/` — orient, status
from evidence, queue grooming, build dispatch, milestone verification and
close (demo → changelog → retro → push *proposal*), release prep — with a
**Training log** the retro skill is now required to append to; an unbroken
log is the proof the training loop is alive. CLAUDE.md points at it as the
umbrella; retro's fold-targets name all three skills.

## Iteration 10 — 2026-08-23 — K8: the braid pipeline

**What now exists:** `compile/` grew its real shape — select.py (filters
compose by intersection; excluded direct deps become stubs), strategies/
(registry + entry-points; linear; grouped with lead/tail pseudo-sections and
group-level-cycle fallback-with-warning), render.py (sandboxed Jinja,
template resolution manifest→pack→default, full context contract), weave.py
(global numbering, cord assembly, blank-collapse), diagram.py (mermaid with
membership subgraphs + dot with clusters), braid.py (check-error gate, --dry),
export.py. `Plan.braid` works via a registration hook so core never imports
compile (the boundary test forced the honest design). CLI verbs `braid` and
`export`.

**Verified:** 13 pipeline tests (102 total at commit), plus an eyeball pass
of real output that caught four issues the assertions didn't: cp1252 stdout
corrupting em-dashes on Windows (artifact writer now forces UTF-8), Python
list reprs in the default template, group nodes duplicated in mermaid, and
cramped cord spacing. All fixed and re-read.

**Lessons:**
- Jinja resolves `dict.items` (the method) before the key named `items` —
  section dicts use `entries`.
- trim_blocks eats the newline after every block tag: put newlines inside
  expression output in inline-composed templates.
- Substring assertions pass on ugly output; **reading the artifact is part of
  verifying a compiler.** Candidate for the iteration skill at the M2 retro.
