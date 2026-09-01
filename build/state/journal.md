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

## Iteration 11 — 2026-08-23 — K9: engineering templates and goldens

**What now exists:** the five pack templates
(`kumihimo/packs/engineering/templates/*.j2`) — tasks with effort/status
badges, honest After lines, See-also links, and Done-when checklists; settled
decisions as stated constraints; open decisions/questions as loud blockers
naming what they block; risks with impact and standing mitigation; milestones
as section intros that don't repeat their own header. Render context gained
`links` (with titles). Goldens frozen for both strategies
(`tests/golden/apiguard-{grouped,linear}.md`) with exact-equality tests.

**Verified:** full grouped AND linear artifacts read end to end (the linear
one had never been looked at before freezing — that reading is the point of
the golden ritual), 104 tests green, gated battery.

**Prompt effectiveness: not verified.** The braid has not yet been run
against a real agent; that claim waits for K11's dogfood or an explicit run.

## Iteration 12 — 2026-08-23 — K11: the roadmap, in Kumihimo — M2 complete

**What now exists:** `plans/roadmap/` — 17 nodes, 25 edges, built through the
real CLI (new → add ×17 → link ×3), all five kinds in use, milestones M3-M6
as sections with true cross-milestone needs. `check`: "17 node(s), 25
edge(s): 0 error(s), 0 warning(s)" (actual output). The M2 demo, run for
real: `kumihimo braid plans/roadmap --in m3-mcp` produced the complete M3
milestone prompt — preamble pointing at CLAUDE.md/CONVENTIONS.md, mermaid
shape, milestone intro with target, both tasks with After lines and
Done-when checklists, epilogue carrying the milestone-close ritual. From
here on, milestone prompts are braided, not hand-written.

**Dogfood findings (the point of dogfooding):**
- The CLI cannot update a node — titles had to go through ops in Python.
  Queued as K16 (`kumihimo set`).
- `kumihimo new`'s starter node gets deleted by hand in every real use;
  fine (files are truth), but `new --bare` might deserve a thought later.

**Prompt effectiveness: partially verified.** The braid was read end to end
and is well-formed and actionable; whether it *steers* an agent well is
verified only when M3 is actually built from it. Claimed exactly that far.

## retro: 1 lesson through iteration 12 — M2 close

Read: iterations 9-12. Folded: **read-the-artifact** (iteration 10's four
eyeball-caught issues) → kumihimo-iteration Step 5, with the goldens named
as where that reading happens for braid changes. Considered, not folded:
Jinja dict.items/trim_blocks specifics (live in code comments beside the
templates, where the next template author will actually be looking).
Nothing pruned. Training log appended in kumihimo-manage.
loop.json: iteration=12, last_retro_iteration=12.

## Iteration 13 — 2026-08-23 — K12: MCP control — M3 complete

**What now exists:** `kumihimo/mcp/tools.py` (behavior as plain functions —
reads with effective fields, the mutation set as ops twins, check, braid
with the full slicing vocabulary, `ready` with the satisfaction rule: own
status todo, deps statusless or done/settled/answered), `server.py`
(MCPServer registration, eleven tools, instructions), `kumihimo mcp` verb,
`.mcp.json` serving plans/roadmap. Built from the braided M3 prompt.

**Verified, live:** a real stdio client session against the real spawned
server — initialize, list_tools returned all eleven, `ready` returned actual
roadmap work, `braid {in_: m3-mcp, dry: true}` compiled over the wire
(outputs pasted in the session log). 111 tests total. Roadmap items
mcp-tools and mcp-config marked done *through the MCP tools themselves*;
`ready` now answers: docs-site, example-nonengineering, server-watch,
wheel-assets.

**Notes:** PLAN.md §6.1 says "ten tools" but lists eleven — the prose count
was wrong; eleven ship. SDK reality check: mcp 2.0.0 renamed FastMCP to
`MCPServer` (mcp.server) — written-from-memory API didn't exist; two minutes
of introspection fixed what an hour of debugging docs might not have. Also:
second time an entry was inserted above the previous one instead of appended
(newest-at-bottom). Both lesson candidates for the M3 retro.

**Incident, third of its shape:** the K12 commit landed with one failing
test because the pytest gate was `pytest | tail -1` — an ad-hoc deviation
from the skill's own written chain. The failing test itself had pinned
mutable roadmap statuses. Both fixed in the follow-up commit; both folded at
the retro below.

## retro: 4 lessons through iteration 13 — M3 close

Read: iteration 13 and its follow-up. Folded: (1) run-the-battery-as-written
with the exact silencing-not-piping chain → iteration skill Step 5; (2)
introspect installed APIs before writing against memory → Step 5; (3)
journal entries append at the bottom → Step 6; (4) tests pin invariants, not
living state → CONVENTIONS.md Verification. Training log appended in
kumihimo-manage. Nothing pruned. loop.json: iteration=13,
last_retro_iteration=13.

## Iteration 14 — 2026-08-23 — server-watch, wheel-assets, canvas-render — M4 complete

**What now exists:** the watching server (GET /api/plan rebuilt from disk
every call; /api/ws initial-then-every-change; churn-filtered watchfiles;
honest fallback page; localhost only), `kumihimo edit`, the React Flow
canvas (frontend/ — kind colors, three edge styles with rel labels, view.yaml
positions + elk + toggle, findings sidebar, node detail, live over WS), and
the wheel path (hatch_build.py force-includes static when present;
`uv build --wheel` is the release artifact).

**Verified, all live:** file edit → WS push in 0.173s carrying the edit
(real server, real socket); disk edit → canvas title updated with no refresh
(watched in the DOM); 7 nodes + all 8 edges by id with labels; view.yaml
transforms exact (translate(40px, 200px) et al.); auto-layout moved all 7;
wheel lists all three static files; clean-venv pip install served the real
canvas HTML + API with no Node. 117 tests green.

**The edge-rendering saga, honestly:** edges rendered in dev and not in the
built page. Two plausible-theory fixes (controlled-mode onNodesChange;
carrying `measured` across rebuilds) didn't cure it — both were still
correct-by-documentation and kept. Instrumenting the store (onInit probe)
produced the fact: `measured` never lands. The environment was the culprit:
the test browser pane never composites, `document.hidden` is true, rAF never
fires, so ResizeObserver-based measurement never runs. The durable fix was
React Flow's SSR recipe — declared node dimensions + static handle geometry —
which makes edge rendering measurement-independent everywhere. An
environment artifact forced a genuinely better implementation.

**Also learned:** hatchling `artifacts` unreliable for gitignored package
dirs under the packages shorthand (hook with force_include instead);
`uv build` default is sdist→wheel so the hook must run against the source
tree (`uv build --wheel`); on Windows, running servers hold the venv's
console-script exe and block uv reinstalls — stop them before building.
Deferred, noted: bundle is 1.8MB (elkjs dominates) — code-split later;
React Flow subflow containment for groups deferred to M5 polish
(membership renders as dashed edges + milestone styling today).

## retro: 2 lessons through iteration 14 — M4 close

Read: iteration 14. Folded: (1) the debugging rule of two — instrument after
the second failed theory, and check renderer reality (visibilityState/rAF)
before theorizing about UI code → iteration skill Step 5; (2) Windows
servers hold the venv exe and block uv reinstalls → iteration skill.
Considered, not folded: packaging facts (artifacts-vs-hook, uv build
sdist→wheel) — they live in hatch_build.py's header and the wheel-assets
roadmap node, where the next packager will actually look. Training log
appended. Nothing pruned. loop.json: iteration=14, last_retro_iteration=14.

## Iteration 15 — 2026-08-24 — editor-ops, editor-conflicts, playwright-smoke — M5 complete

**What now exists:** the write path end to end. Server: POST /api/ops (one
discriminated-union envelope per gesture, single-writer lock, digest 409s
that clobber nothing, positions to view.yaml only — sorted, flow-style),
GET /api/braid, GET /api/dirty; payload nodes carry digests. Frontend: drag
(→ view.yaml), connect with a needs/in/link mode selector, add-node form,
NodeForm (title, kind, schema-driven fields, body, save-with-digest, rename,
delete), edge removal, braid modal with copy, dirty indicator, conflict
notices. Product fixes found by driving it: rebuild-freeze while a gesture
is in flight (a payload echo mid-drag cancelled the gesture), fitView zoom
capped at 1.25 (a three-node plan zoomed to 2x pushed handles off-viewport),
12px handles (6px targets are brutal for humans and robots alike).

**Verified:** 7 ops-API tests including a full HTTP editor session leaving
byte-canonical files and a 409 that preserved the concurrent edit; the
Playwright smoke PASSING in real headless chromium — three nodes added via
form, two needs edges drawn handle-to-handle, a schema-driven field saved,
a node dragged into view.yaml, the braid read out of the modal with correct
order, and the build.md file byte-equal to its canonical form. 125 tests
total. The roadmap's concurrent-writers question answered (no proxy in
v0.1) through the MCP tools.

**Test-craft lessons, some at my own expense:**
- The first smoke draft wrapped the whole browser block in
  `except Error: skip` and laundered a real failure into a 37-second
  "skip". Skips guard exactly one precondition; everything else fails.
- Terminating a `uv run` wrapper on Windows orphans the real server, which
  then squats on the port — spawn the venv exe directly.
- Playwright counts SVG edge groups as "hidden"; wait state="attached".
- Field selects are addressed by label, not index (the pack's field order
  is not the form's contract).
- The minimap overlays the canvas corner; drag the leftmost node.

## retro: 2 lessons through iteration 15 — M5 close

Read: iteration 15. Folded: (1) a skip guards exactly one precondition —
everything else fails loudly → iteration skill Step 5; (2) spawn the venv
exe, not the `uv run` wrapper, for terminable test servers → the Windows
note. Considered, not folded: Playwright/React Flow specifics (attached vs
visible, label-addressed selects, minimap overlay) — they live as comments
in the smoke test, where the next e2e author will look. Training log
appended. Nothing pruned. loop.json: iteration=15, last_retro_iteration=15.

## Iteration 16 — 2026-08-24 — K16: kumihimo set

**What now exists:** the update verb the roadmap dogfood found missing —
title, kind, body, priority, --field with the same spec-driven coercion as
add, --unset. parse_fields promoted to the cli layer's shared surface.
**Verified:** 8 CLI tests (126 total), gated battery.

## Iteration 17 — 2026-08-24 — K15: the release pass — M6 prepared

**What now exists:** the docs site (mkdocs-material: ten-minute tutorial,
concepts, how-tos for custom kinds / Claude-over-MCP / the editor, reference
for CLI, file formats, MCP tools, and the Python API via mkdocstrings) —
`mkdocs build --strict` clean in 1.4s; `examples/fieldnotes` (8 nodes,
4 manifest-only kinds, one inline template, 0 findings — PLAN §10.4's
agnostic-core test passed with zero core changes); CI grown to four jobs
(matrix checks, frontend typecheck+build, real-browser editor smoke, strict
docs); docs.yml deploying Pages on push to main; release.yml publishing
sdist + canvas-carrying wheel on tag via trusted publishing; README rewritten
to the truth (everything on it now works); RELEASING.md checklist.

**Verified:** mkdocs strict build (real run), fieldnotes checked and braided
(real output read: the manifest's inline template renders), 128 tests green
including the browser smoke, gated battery.

**Remaining for v0.1, all Thomas's acts by design:** create the public repo
and push; PyPI pending-publisher + Pages one-time setup; version cut; tag.
The roadmap's `ready()` is empty — the plan itself says the tool's work is
done.

## retro: 0 lessons through iteration 17 — M6 close

Read: iterations 16-17. Nothing durable to fold: both iterations executed
the existing rules without incident (the gates gated, artifacts were read,
numbers came from runs). Honest empty retro per the retro skill — the
cadence stays trustworthy precisely because this entry exists. Training log
appended. loop.json: iteration=17, last_retro_iteration=17.

## 2026-08-24 — published: tzavislan/kumihimo, CI green

Thomas said "get it pushed." Public repo created, all 31 commits pushed,
topics set. First-ever CI run (and first-ever Linux run of the suite):
matrix checks, frontend, and docs green immediately; the editor smoke's
*test* passed on Linux but its fixture teardown errored (.venv/bin vs
.venv/Scripts, and uv-run shielding uvicorn from SIGTERM) — fixed with
cross-platform script resolution and TERM→KILL escalation. Second run:
**all five jobs green, exit 0, in 1m13s worst-job**. The docs *deploy*
workflow alone waits on Thomas enabling Pages.

One process note for the next retro window: the piped-exit-code shape
appeared a fourth time, in the `gh run watch | tail` command — a watch, not
a gate, so nothing was committed on it, but the rule generalizes: any
command whose exit code you intend to read gets no pipe.

## 2026-08-24 — outside review response: install truth, npm-on-Windows

An external review (verified against the live repo and index) found the
README's first command, `pip install kumihimo`, fails — the package was
never published (no tags, no releases; release.yml has never fired). Its
second claim, docs-404/failing-workflow, was true when written and already
cured by the Pages enablement. Fixes, verified in a clean GitHub clone
end-to-end: both quickstarts now install from source with no package-index
implication; and running the quickstart the reviewer's way surfaced a second
defect — `npm --prefix <dir> install` silently no-ops on Windows (exit 0, no
node_modules; works on Linux, which is why CI stayed green). All user-facing
npm instructions switched to the cd form, including the server's own
"frontend not built" fallback page. Clean-clone verification: quickstart to
served canvas, CLI battery, 128/128 tests including the browser smoke, all
five docs-site pages live. Lesson for the next retro: clean-machine
verification belongs to every user-facing instruction, not just code — the
README is an interface with its own platform matrix.

## 2026-08-24 — process hardening (Thomas): docs and git move with every upgrade

Thomas's standing rule, encoded where rules survive: CLAUDE.md (push at
every milestone close is now standing-approved; docs ship with the change,
not after), kumihimo-iteration Step 6 (user-visible changes update their
docs-site page in the same commit; UI changes flag a screenshot re-shoot),
kumihimo-manage milestone close (a docs gate before the push: strict build,
named pages, re-shot screenshots, clean-checkout re-verification of changed
README commands), and the Training log. PLAN2.md — still uncommitted,
awaiting his markup — carries the same guarantee as its §6, and grew §3.6
(training the crew: trains: mentions, trained/cadence fields, staleness as
a query never a check) and §3.7 (RAG both directions: JSONL export of
plans for indexers, reference nodes with retrievers, per-agent grounding
lines in --for braids; the library still never retrieves) at his direction.

## Iteration 18 — 2026-08-24 — K17: design tokens + dark mode (builder/checker/critic loop)

First pass of Thomas's builder→checker→critic→train loop on cheaper models
(Sonnet subagents; Fable orchestrates and gates). Builder delivered the token
system (light :root, dark [data-theme] override, color-scheme, RF --xy-*
retinting) and self-caught a specificity bug via live computed-style checks.
Checker: REVISE (1 blocking — typography had zero tokens against an
"every color/space/type decision" acceptance; 4 minors). Critic (screenshots,
both themes, four shots): PASS with 3 contrast/theming nits. One fix round
closed all five (type tokens, toggle styling, milestone id contrast, edge
labels de-inlined so themes can reach them, attribution badge themed).
Deferred to K18 by design: KIND_COLORS + in/link stroke hexes in tsx.
Noted, not fixed: OS theme-change pickup after first persist; one-frame
light flash on dark-preferring OS (useEffect vs useLayoutEffect).

**Verified by me, not the builder:** full battery green (128 tests incl. the
browser smoke against the rebuilt frontend), lint clean. Builder's own
evidence: computed styles read in the live browser in both themes.

## Iteration 19 — 2026-08-24 — K18: edge legibility (builder/checker/critic loop)

Builder (Sonnet): four named ports per node (needs left/right, in/link
bottom→top), tokenized edge strokes with dark overrides, 18px themed
arrowheads on needs+in, cursor-following hover tooltip speaking in titles
("Rate-limit middleware needs v2 endpoint surface"), edge panel with
jump-and-center via the RF instance ref, and a shared parseEdge replacing
three duplicated id-parsers. Checker: REVISE (1 blocking — the tooltip
wedges when a live payload update removes the hovered edge under a parked
cursor, live-reproduced; 1 minor — stale @design tags). Critic (five real
screenshots incl. the 30-node roadmap): PASS, 4 minors — always-visible
port dots clutter dense graphs, in/link share physical ports, fixed-direction
membership routing loops behind cards, and the roadmap's membership tangle
that K19 focus and K20 zoom exist to solve. Orchestrator applied the fix
round directly (clock): tooltip reconciled against the edge set (first
attempt hit the TDZ — effect must sit below the edges memo), tags refreshed.

Deferred with eyes open: port-dot visibility gating (hover-only handles hurt
connect discoverability — needs design, not a hotfix), in/link port
separation, smarter membership routing.

**Gated by me:** typecheck, build, ruff, mypy, 128 tests, lint — green.

## retro: the delegated loop itself — through iteration 19

Thomas's 90-minute builder→checker→critic→train box: two M7 items shipped
end-to-end (K17 tokens+dark, K18 edge legibility), six Sonnet agents,
~1.16M subagent tokens, two blocking finds (one from acceptance-vs-diff
reading, one live-reproduced in the running app), zero battery failures at
the gate. Folded: the Delegated iterations section into kumihimo-iteration
(the pattern, the evidence bar for checkers, the read-the-pixels bar for
critics, the never-delegate-the-gate rule). Training log appended.
loop.json: iteration=19, last_retro_iteration=19, session guard cleared.
M7 stands 2/6 done; K19 (focus cones) is next and unblocked. No push —
milestone-close pushes only, and M7 is open.

## Iteration 20 — 2026-08-24 — K19: focus cones + trace (delegated loop)

Builder (Sonnet): cones.ts pure BFS module, double-click focus (3-step
distance fade, 15% dim, edges follow), alt-click trace with sidebar summary
and no-path notice, Esc/pane-click exits, lenses as pure view state that
survive payload echoes and self-clear only when their nodes vanish. Builder
pre-flagged the cone-hue coincidence in its own report. Checker: PASS with
real rigor — 16 synthetic fixture assertions on the BFS/paths math, live DOM
assertions on apiguard (exact cone membership 8/8, trace path 3/3, echo
persistence via out-of-band POST), and it caught+reverted its own transient
view.yaml write. Critic (four screenshots incl. the 30-node roadmap):
REVISE, 1 blocking — the pre-flagged collision, pixel-confirmed: cone amber
was byte-identical to the decision kind hex, cone teal to question — plus
undimmed edge labels and a flat-gray minimap. Fix round (same warm builder,
105s): cones now fuchsia/lime (distinct from all five kind hues), labels dim
with their edges, minimap paints kind colors with dimmed-aware alpha (one
deliberate literal — canvas can't resolve var(); commented).

**Gated by me:** ruff, mypy, 128 tests, lint — green. Loop note: the
builder's deviation-flag was the critic's blocking find — flags in builder
reports deserve immediate weight, not later rediscovery.

## Iteration 21 — 2026-08-24 — K20: semantic zoom (delegated loop)

Builder (Sonnet): three tiers branched in KumiNode on a data-carried tier,
onMove updating state only on boundary crossings, per-payload memberCounts/
acceptance plumbing, and a real catch — React Flow's default minZoom (0.5)
sat above the far threshold (0.45), making the far tier unreachable dead
code; minZoom now 0.2, commented. Checker: PASS (1 minor — docs footprint
overclaim), verified threshold hysteresis, plumbing regression-risk on the
rewritten nodes effect, and that onMove cannot reintroduce the mid-gesture
rebuild bug (interacting guards first). Critic: REVISE — near-tier cards
grew past the 66px box and visibly fused on the roadmap at default density
(the "accepted for v0.2" comment did not survive being looked at), plus a
"missing halo" find that was actually a two-source acceptance collision:
PLAN2 §2.2's mid-tier prose mentions finding halos, the queue split gives
them to K21, and the roadmap node quoted the prose. Fix round: near tier
now fits INSIDE the fixed box — smaller layout-px type that zoom >=1.3
magnifies back to readability, one-line preview, first-acceptance-item
"+n more" — self-verified live: 30/30 roadmap nodes at exactly
offsetHeight 66, scrollHeight 64, at zoom 1.743. Roadmap node's acceptance
reworded (by the orchestrator) to name K21 as the halo's home; the builder
independently flagged that concurrent edit as not-its-own — the
account-for-every-line discipline observed by a subagent.

Far-tier long-title truncation noted as acceptable silhouette behavior.

**Gated by me:** ruff, mypy, 128 tests, lint — green.

## retro: delegated loop #2 — through iteration 21

Box 19:41-20:55 (~74 min): K19 focus/trace and K20 semantic zoom shipped
end-to-end; six Sonnet agents (~1.16M subagent tokens this box); two critic
blockings, both real, both fixed same-iteration; checker rigor peaked at 16
synthetic assertions plus live DOM proof. Folded: triage builder flags,
acceptance-has-one-home, accepted-tradeoffs-expire (iteration skill);
queue-is-acceptance-authority (manage skill). M7 stands 4/6 — K21 finding
halos and K22 palette remain, both unblocked (K22's dep K19 is done).
loop.json: iteration=21, last_retro=21, guard cleared. No push — M7 open.

## Iteration 22 — 2026-08-24 — K21: finding halos + click-to-jump (delegated loop)

Builder (Sonnet): findingHalos map (error beats warning; file-level findings
structurally can't halo — same Set gates sidebar clickability), halo ring as
box-shadow so it composes with focus outline / dim opacity / kind stripe
without contention, click-to-jump reusing the edge panel's jumpTo, "Check:
clean" empty state, halo tokens as color-mix derivations of the existing
severity tokens (declared once — nested var() re-resolves per theme).
Builder live-verified on a throwaway broken plan incl. hand-computed
centering math. Combined checker+critic (small-item variant, noted): PASS,
1 minor — the far-tier ring hugged the empty layout box instead of the
shrunken chip; orchestrator fixed (ring the chip at far tier). The reviewer
also could not screenshot (hidden pane, the known environment artifact),
said so plainly, and verified via live computed styles instead — the
honesty bar holding in a subagent.

**Gated by me:** typecheck, build, ruff, mypy, 128 tests, lint — green.

## Iteration 23 — 2026-08-24 — K22: Ctrl+K palette + graph keyboard (delegated loop)

Builder (Sonnet): Palette.tsx (substring search over id/title/body with
title/id ranked above body hits + context snippets, four commands, full
keyboard+mouse driving), graph-directional keys (Left=dependency,
Right=dependent, Up/Down=siblings, F=focus, Del=confirm-then-remove via
ops), input-target guard, and a necessary unbriefed fix: React Flow's own
deleteKeyCode/keyboard-a11y handlers would have locally deleted nodes
BYPASSING core.ops and nudged positions on arrows — disabled, confirmed
live. Deviations recorded per invariant: PLAN2 prose said up=dependency —
the canvas's needs axis is horizontal since K18, so Left/Right carry
direction and Up/Down walk siblings (documented in both doc pages);
substring-not-fuzzy search is a no-new-deps judgment call. docs/reference/
shortcuts.md tables the full gesture inventory; mkdocs strict green.
Checker+critic (combined, playwright-not-pane per the tooling note): PASS,
2 minors — this journal entry (now written), and mid-word snippet
truncation (documented fixed-radius design; accepted). Covered the
builder's untested branches: palette row mouse click, and Delete with the
dialog accepted (file really removed via ops on a throwaway plan) and
dismissed (file survives).

Builder flags triaged per the trained rule: App.tsx over the cap (~784) →
@exempt note (reviewer=thomas-pending) + K23 split queued before M8; TS
files unlinted despite CONVENTIONS' promise → K24 queued. The flag-triage
rule paid for itself one loop after it was written.

**Gated by me:** ruff, mypy, 128 tests, lint, mkdocs strict — green.

## M7 close + retro — 2026-08-24, through iteration 23

**Demo, run for real on plans/roadmap in dark mode (actual outputs):**
focus on semantic-zoom -> upstream=['tokens-dark'],
downstream=['crew-work','feel-work','shape-work'], dimmed=25, hint
"Focused on Three-tier semantic zoom — upstream 1, downstream 3. Esc to
exit."; silhouette 30/30 nodes at far tier; palette body-only query
"distance fade" -> found focus-cones with snippet, Enter selected it. Two
demo-script fumbles were mine, not the product's (wrong selector, then a
query that existed only in source code) — the checker had driven both paths
correctly an hour earlier.

**Docs gate:** mkdocs strict green; editor.md grew per-item sections all
milestone; shortcuts reference shipped with K22; all three screenshots
re-shot (the hero now shows near-tier cards, glyphs, ports, and the theme
toggle); README commands unchanged so no clean-checkout re-verification
owed. CHANGELOG M7 entry written.

**Retro folded:** small-item combined checker+critic variant; playwright-
not-pane screenshot tooling note. Flag-triage validated in the wild (K23,
K24 born from builder flags). loop.json: iteration=23, last_retro=23,
guard cleared. M7 complete 6/6; next up K23/K24 hygiene, then M8 shape-work
split. Pushing at milestone close per standing say-so.

## Iteration 24 — 2026-08-24 — K23: App.tsx split (delegated loop)

Builder (Sonnet): pure extraction refactor — edges.ts (127 effective),
derive.ts (74), useGraphKeyboard.ts (89), theme.ts (19); App.tsx from 1049
physical/784 effective down to 691/522, @exempt removed. Zero behavior
change proven three ways: typecheck, build, and the editor smoke driving
the real UI. Comment accuracy maintained beyond the moved files (KumiNode/
styles.css pointers re-homed); historical records left frozen. Judgment
calls stated and sound (nodeTitle/colorFor to derive.ts, lens types with
their only reader, theme as a hook with unchanged call order). Reviewer
skipped per the small-item variant: a pure move with the smoke green IS the
check; no pixels intended to change so no critic.

**Gated by me:** ruff, mypy, 128 tests, lint — green.

## Iteration 25 — 2026-08-24 — K24: the linter learns TypeScript (delegated loop)

Builder (Sonnet): TS discovery (frontend top-level + src recursive, .d.ts
included), header extraction with JSDoc-gutter normalization feeding the
SAME tag parser, line-based effective-line cap with its imprecision
documented in three places, exemptions with gutter tolerance proven a no-op
for Python, README indexes for TS folders, two hand-written frontend
READMEs, 11 new lint tests. On the real tree: all 15 TS files already
compliant — the conventions held by habit before they were enforced, which
is the best possible audit result. CONVENTIONS.md realigned to what is
actually enforced (no per-function @purpose for TS — no parser dep; scoped
honestly rather than overpromised). The builder's own new prose tripped the
exempt-grammar check mid-build and it fixed the prose, not the check.

**Gated by me:** ruff, mypy, 139 tests, lint (now covering TS) — green.

## Iteration 26 — 2026-08-24 — K25: containers (delegated loop, the M8 spike)

Build round (Sonnet, 40 min): real RF parent containers for any in-target,
collapse chips with n/m done, edge reroute+dedupe with self-loop dropping,
view.yaml `collapsed` key (absolute positions untouched), set_collapsed op,
payload plumbing — plus a live-caught RF coupling (draggable:false disables
onNodeDoubleClick) fixed mid-pass. Spike verdict round 1: collapsed = real
elk substitution; expanded = documented fallback (flat elk + retroactive
boxes).

Review: checker REVISE (1 blocking — dragging one member corrupted
view.yaml, wrong X plus an UNREQUESTED sibling entry, reproduced twice with
numbers; 4 minors) and critic REVISE (2 blocking — retroactive boxes
overlapped siblings on 3 of 8 real milestones, M5's members rendered inside
M6's frame; collapsed chips landed on other milestones' headers after
auto-layout; "trades spaghetti edges for spaghetti boxes"). All three
blockings shared the deferred-fallback root cause.

Fix round (same warm builder): drag-stop reads RF's own committed
positionAbsolute via getInternalNode (verified against installed source
that it commits before the handler fires) — one node dragged, one entry
written, exact to the pixel at two magnitudes; expanded containers became
REAL elk compound nodes (padding for the title bar, hierarchyHandling
INCLUDE_CHILDREN, edges flat at root — the LCA fear dissolved exactly as
briefed) — 28/28 pairwise zero-overlap expanded AND mixed-collapsed;
set_collapsed validates ids as existing containers (400 otherwise);
payload filters stale collapsed ids; the critic's "miiestone" pill was
DOM-adjudicated a screenshot artifact. Reviewer evidence re-run by the
builder as numeric assertions; no third round needed. Deferred with owners:
four interaction items folded into K26's queue text; checker's one
mistaken Browser-pane call self-caught and flagged — transparency holding.

**Gated by me:** ruff, mypy, 143 tests, lint, mkdocs strict — green.
App.tsx 585/600 effective, no exemptions anywhere.
