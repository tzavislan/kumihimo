# Build queue

The work, in order. One item per iteration. Statuses: `todo`, `doing`,
`done`, `split`, `blocked`, `needs-thomas`. An item is eligible when every id
in `needs:` is `done`. Milestones and acceptance detail: PLAN.md §9.

---

## M0 — Bootstrap

### K0 — Repo scaffold, conventions linter, CI, skills, state
status: done (iteration 1)
needs: —
PLAN.md §9 M0. Package skeleton with tagged headers and folder READMEs;
`kumihimo --version`; `tools/lint.py` (cap, tags, README indexes, @exempt)
with behaviour tests; boundary tests; CI on ubuntu+windows; CLAUDE.md,
CONVENTIONS.md, CONTRIBUTING.md, CHANGELOG.md; both skills; this state.

## M1 — Core model and store

### K1 — Model types and kind system
status: done (iteration 2)
needs: —
PLAN.md §3.1-3.2. `core/model.py` (Node, Plan data, Finding), `core/kinds.py`
(KindDef, FieldSpec, pack loading + manifest overrides), `kumihimo/packs/
engineering/kinds.yaml` (task, milestone, decision, risk, question schemas).
Accept: field validation errors are precise (node, field, why); packs load by
name; unknown-kind is a Finding, not a crash.

### K2 — Store: load and byte-fidelity save
status: done (iteration 3)
needs: [K1]
PLAN.md §3.3. Parse `kumihimo.yaml` + `nodes/**/*.md` (frontmatter via
ruamel round-trip, body raw); save preserves untouched files byte-for-byte,
preserves frontmatter comments/order and the file's own newline style.
Accept: golden round-trip tests over nasty fixtures (comments, CRLF, unicode,
odd indentation) pass load→save unchanged.

### K3 — Graph: deterministic order, slices, cycles
status: done (iteration 4)
needs: [K1]
PLAN.md §4.1 step 2. Kahn with sorted ready-queue, ties by (priority desc,
id asc); ancestors/descendants cones; cycle detection that names the path.
Accept: order is identical across OS/Python; cycle error lists the cycle in
edge order.

### K4 — Validation (`check` findings)
status: done (iteration 5)
needs: [K2, K3]
PLAN.md §3.4. Every listed error and warning as Findings with node/file
context. Accept: each rule has a test that triggers it and one that doesn't.

### K5 — Ops layer
status: done (iteration 6)
needs: [K2]
PLAN.md §7.1 invariant 1. add_node, update_node, link, unlink, rename
(referrer fixup incl. view.yaml), remove — each atomic, each returning what
changed. Accept: rename fixes every referrer; ops on a missing node fail
cleanly; nothing bypasses store save.

### K6 — CLI verbs: new, add, link, check
status: done (iteration 7)
needs: [K4, K5]
PLAN.md §1. `new` scaffolds manifest+nodes/ with the engineering pack; `add`
and `link` are flag-driven (no editor spawning); `check` prints Findings via
rich with exit code. Accept: the M1 demo path works end to end.

### K7 — API-Guard example + M1 demo test
status: done (iteration 8) — M1 complete
needs: [K6]
PLAN.md §3.3 worked example as `examples/apiguard/`, built via the CLI, with
an integration test: build, validate, introduce a cycle, watch `check` name
it; a field edit touches one line in git diff.
Accept: matches the plan's worked example; doubles as fixture for M2 goldens.

## M2 — The braid (coarse; split before starting)

### K8 — Braid pipeline: select, order, render, weave + linear/grouped
status: done (iteration 10)
needs: [K7]

### K9 — Engineering pack templates + goldens
status: done (iteration 11)
needs: [K8]

### K10 — Mermaid/DOT export + `--dry`
status: done (landed inside K8's commit — export verb, diagram module, --dry)
needs: [K8]

### K11 — Dogfood: plans/roadmap/ in Kumihimo
status: done (iteration 12) — M2 complete
needs: [K9]

### K16 — CLI `set` verb (update titles/fields/body from the shell)
status: done (iteration 16)
needs: —
Discovered while dogfooding K11: the CLI can create and link nodes but not
update them — roadmap titles had to go through the ops layer in Python.
Mirror `ops.update_node` as `kumihimo set PLAN ID [--title] [--body]
[--field k=v] [--unset k] [--kind]`. PLAN.md §1 (CLI), §7.1 invariant 1.

## M3+ (coarse)

### K12 — MCP server (eleven tools, .mcp.json)
status: done (iteration 13) — M3 complete
needs: [K9]

### K13 — Editor server: watch + WebSocket + read-only canvas
status: done (iteration 14) — M4 complete
needs: [K9]

### K14 — Editor write path (frozen surface, PLAN.md §5.3)
status: done (iteration 15) — M5 complete
needs: [K13]

### K15 — v0.1 release pass (docs site, examples, PyPI)
status: needs-thomas (iteration 17) — everything preparable is done
needs: [K12, K14]
Docs site built strict-clean; fieldnotes example proves the agnostic core;
CI grew frontend/smoke/docs jobs; docs.yml deploys Pages; release.yml
publishes on tag via trusted publishing. Remaining acts are Thomas's alone:
create the GitHub repo and push, PyPI pending-publisher + Pages one-time
setup, version cut, tag. Checklist: RELEASING.md.

## M7 — See (PLAN2.md §2, split 2026-08-24)

### K17 — Design tokens + dark mode
status: done (iteration 18)
needs: —
PLAN2 §2.5. CSS custom properties for every color/space/type decision in
frontend/src/styles.css; prefers-color-scheme + a toggle button; both themes
coherent (canvas, sidebar, node cards, modal, minimap). Accept: toggle works;
no hardcoded hex left outside the token block; screenshots readable in both.

### K18 — Ports, arrowheads, edge hover/selection
status: done (iteration 19)
needs: [K17]
PLAN2 §2.4, §2.1. needs=left/right ports, in=top, links=bottom; scaled
arrowheads; hover thickening + tooltip naming both ends and relation; edge
click opens a sidebar edge panel (endpoints with jump, relation, delete).
Accept: apiguard's membership edges no longer share dependency ports; hover
and panel behaviors verified in the smoke or a screenshot pass.

### K19 — Focus cones + trace
status: done (iteration 20)
needs: [K18]
PLAN2 §2.1. Double-click focuses: ancestors one tint, descendants another,
distance fade, rest dimmed to 15%, Esc restores; alt-click second node lights
all paths between. Client-side cones over payload needs edges.
Accept: focus on rate-limit-core tints exactly its cones; Esc restores.

### K20 — Semantic zoom
status: done (iteration 21)
needs: [K17]
PLAN2 §2.2. Far=shape+title, Mid=upgraded card (status glyph, effort chip,
member count, halo), Near=body preview + acceptance checkboxes + chips;
thresholds on RF zoom. Accept: three tiers visibly distinct on the roadmap.

### K21 — Finding halos + click-to-jump
status: done (iteration 22)
needs: [K17]
PLAN2 §2.1. Error/warning halos on nodes; sidebar findings click to select
and center. Accept: a plan with one error shows exactly one red halo; click
centers it.

### K22 — Ctrl+K palette + graph keyboard
status: done (iteration 23) — M7 items complete
needs: [K19]
PLAN2 §2.5. Fuzzy palette over id/title/body, select-and-center; command
entries (add node, braid); arrows walk the graph (up=dependency,
down=dependent), F focuses, Del prompts removal. Accept: palette finds by
body text; arrow-walk follows edges not screen positions.

### K23 — Split App.tsx under the cap
status: done (iteration 24)
needs: —
Discovered at K22 (builder flag): App.tsx is ~784 lines, over the 600 cap
CONVENTIONS.md applies to every language. Extract by responsibility (edge
helpers, keyboard, lens state?) into focused modules with headers; must land
before M8's shape-work piles more on. Accept: every frontend file under 600
effective lines; typecheck/build/smoke green.

### K24 — Conventions linter learns TypeScript
status: done (iteration 25)
needs: —
Discovered at K22: tools/lint.py scans only Python; CONVENTIONS.md promises
TS header linting "from M4" and nothing enforces it — the exact rot the
linter exists to prevent. Extend to frontend/src/*.ts(x): @file header
presence/path match, cap with comment/blank exclusion (JSDoc + //), @exempt
grammar. Accept: seeded TS violation fails CI; current tree passes (after
K23).

## M8 — Shape (PLAN2.md §2.3-2.4, split 2026-08-31)

### K25 — Containers: milestones as subflows with collapse
status: done (iteration 26)
needs: —
PLAN2 §2.3 lens 1; risk 1's spike. RF parent/child containers for in-groups;
collapse state in view.yaml; collapsed milestone = chip (n/m done) with
edges re-routed to it; stored positions stay ABSOLUTE (sidecar format
unchanged) — relative conversion only inside the RF layer. Fallback if
subflows x elk won't stabilize: containers without elk-into-containers,
documented. Accept: roadmap renders M7 as a container; collapsing it to a
chip survives reload and echoes; no view.yaml format change.

### K26 — The lens bar (Structure/Status/Flow/Risk)
status: done (iteration 27)
needs: [K25]
PLAN2 §2.3. Lens switcher in the sidebar; Status draws the ready frontier
(glow) and dims done; Flow bolds the critical path; Risk enlarges open
decision/question/risk with descendant shading. Precedence with focus/halos
documented. Accept: each lens visibly distinct on the roadmap; ready glow
matches MCP ready() output exactly.
Inherits four K25 deferrals (review evidence in iteration 26's journal):
keyboard/palette jump to a hidden member must select the collapsed container
and center it (today: sidebar detaches from canvas); focus/trace tinting
must see through rerouted edges and tint the chip; container focus should
union its members' cones instead of reading upstream 0/downstream 0; edge
interaction hitboxes can intercept the container toggle click (z-order).

### K27 — Lanes, partial re-layout, echo glides
status: done (iteration 28) — M8 items complete
needs: [K25]
PLAN2 §2.3-2.5. Depth-lanes layout option; re-layout selection only
(through set_positions); payload echoes animate transforms (suppressed
mid-drag). Accept: glides visible on an MCP-driven edit; partial re-layout
leaves unselected positions untouched in view.yaml.

## M9 — Crew (PLAN2.md §3, split 2026-09-01)

### K28 — Crew model: three mention keys, three kinds, prose mentions
status: done (iteration 29)
needs: —
PLAN2 §3.1-3.2, §3.6-3.7 (model half). RESERVED_KEYS grows agents/skills/
trains (scalar-or-list, like needs/in); Node carries them; validation:
targets must exist, agents:->kind agent, skills:->kind skill, trains:->agent
or skill, all as errors; engineering pack gains agent (runtime choice
[claude-code, cloud, human, other], model str, entry str, scope list,
retrieval str, trained str), skill (invocation str, source str, cadence str,
trained str), reference (locator str, retriever str); @id prose mentions
scanned READ-ONLY from bodies (one documented regex; dangling @id = warning;
bodies never rewritten — PLAN2 §3.2's line); ops.link/unlink accept
agents=/skills=/trains= (no cycle guard — mentions are not ordering edges);
format stays 1 (additive keys; older readers warn as unknown fields).
Accept: round-trip fidelity holds for the new keys; every validation rule
has a trigger and non-trigger test; a v0.1-style file with agents: loads
with a warning, not corruption.

### K29 — Braid --for, Cast section, crew surface, JSONL export
status: done (iteration 30)
needs: [K28]
PLAN2 §3.3, §3.6-3.7 (compile half). Task templates render *Assigned:* /
*With:* / *Trains:* lines; consult-links (links rel=consult to reference
nodes) render *Consult:* title — locator (via retriever); grouped strategy
gains a Cast section when agent/skill nodes are selected (each with
invocation/entry, trained, cadence); braid --for AGENT: selection = nodes
mentioning that agent + context stubs + its skills' nodes, work orders open
with *Ground with:* from the agent's retrieval field; kumihimo crew (CLI) +
crew MCP tool: the roster with trained/cadence/mention counts — dates
emitted, never compared to now (no clock in the library); ready(for_agent=)
filter; kumihimo export --format jsonl (one line per node: id, kind, title,
body, effective, edges incl. mentions). Goldens regenerated and READ.
Accept: --for output opens with the grounding line; crew lists the roster;
jsonl round-trips through json.loads line by line; check gate still holds.

### K30 — Crew lens, mention edges, chip editors
status: done (iteration 31)
needs: [K28]
PLAN2 §3 (canvas half). Payload + ops envelopes carry the three mention
keys; mention edges render distinctly (thin, labeled, own class/tokens; no
ordering ports — bottom-to-top like links); Crew lens (5th): nodes tinted
by first assigned agent, skill chips at near tier, unassigned WORK (task
kind, no agents:) outlined, trains edges emphasized; sidebar gains chip
editors with id autocomplete for needs/agents/skills (add/remove chips ->
link/unlink ops). Accept: roadmap-with-crew renders legibly under the Crew
lens; chip edit round-trips through ops; lens count stays capped at five.

## M10 — Feel (PLAN2.md §2.5 + §4 M10, split 2026-09-03)

### K31 — Attribution toasts + change pulses
status: done (iteration 32)
needs: —
PLAN2 §2.5 Motion & attribution. Ops layer appends one JSON line per
mutation to `<plan>/.kumihimo/events.jsonl` — {actor, op, targets}, NO
timestamp: the library stays absolutely clock-free (zero datetime imports
today, zero after; the editor correlates by tailing from its last file
offset, which is all attribution needs) — actor set explicitly by each
thin client (CLI "cli", MCP "mcp", HTTP ops API from the editor "editor");
the dir is created on demand, gitignored by scaffold (and .gitignore gains
it for existing plans), log truncated to the last 200 events on write. Editor: the
watcher-driven payload refresh diffs node digests old→new; changed/added/
removed nodes raise ONE toast naming the source when known ("via MCP:
crew-model updated"; unattributed = "outside edit") and pulse the changed
nodes (CSS animation ~1s, none under prefers-reduced-motion); the editor's
own ops (actor "editor") raise no toast — the payload echo is already its
acknowledgment. Toast stack: top-right, newest on top, max 4 visible,
auto-dismiss ~6s, dismiss-on-click, both themes via tokens.
Accept: an MCP/CLI mutation while the editor is open produces exactly one
attributed toast + pulse on the right nodes (proven in a real browser);
editor self-ops produce zero toasts; events.jsonl never enters git status
on a fresh scaffold; check/braid outputs are byte-identical with and
without the log present.

### K32 — Inverse-op undo trail
status: done (iteration 33)
needs: —
PLAN2 §2.5 Undo trail, §5 risk 4. ops_api op responses gain an `inverse`
envelope computed from before-state: add↔remove, set-field↔set-prior (or
unset), link↔unlink, rename↔reverse rename, set_positions/set_collapsed↔
prior values; remove_node returns inverse: null (honestly not undoable in
v0.2 — git is; the trail says so). Each inverse carries the digest(s) it
preconditions on. Frontend: a session-scoped Undo panel listing applied
ops newest-first (this session only, in-memory); each entry enabled while
its precondition digests match the current payload, else grayed with why
("crew-model changed since"); click posts the inverse through the normal
ops door (it then appears on the trail itself); Ctrl+Z fires the topmost
enabled entry; keyboard docs updated.
Accept: add→undo removes; set→undo restores the prior value byte-for-byte
in the file; rename→undo renames back with referrers re-fixed; a later
external edit grays the stale entry with the reason; undo of undo works;
all through POST /api/ops with zero new write paths.

### K33 — Styled braid preview
status: done (iteration 34)
needs: —
PLAN2 §4 M10. The braid modal renders the compiled Markdown styled
(headings, lists, code, tables, blockquotes) with the existing tokens in
both themes; keeps Copy, gains Download (.md, the exact bytes — no
re-serialization); a Raw/Rendered switch; and a toggle collapsing the
plan-shape mermaid block (rendering mermaid itself stays OUT — ~1MB
against K34's budget; the toggle folds the fenced block, documented).
The Markdown renderer is a small dependency lazy-loaded with the modal
(chunk never in the initial bundle).
Accept: preview of plans/roadmap reads as a document in light and dark
(critic-judged on real shots); Download bytes == braid API bytes
(sha256); initial bundle size unchanged (renderer chunk loads on first
modal open, proven in the network log).

### K34 — Elk lazy-load + both-theme screenshots
status: done (iteration 35)
needs: —
PLAN2 §4 M10. elkjs moves to dynamic import (layout awaits it on first
use; a loading state if perceptible); vite manualChunks splits vendor
weight so the INITIAL JS payload lands under ~700KB (measure before/after,
record numbers in the journal; the >500kB chunk warning gone or justified
in writing). tools/screenshots.py shoots dark-theme variants (suffix
-dark) of canvas-roadmap, lens-status, lens-crew by toggling the editor
theme control; docs embed light+dark pairs where mkdocs-material supports
it (#only-light/#only-dark image classes) for the README hero and editor
page.
Accept: cold-load network log shows elk fetched only when a layout runs;
bundle numbers in the journal; dark shots in docs/assets wired into at
least the editor page; editor-smoke CI still green.

### K35 — v0.2 release prep
status: done (iteration 36)
needs: [K31, K32, K33, K34]
PLAN2 §4 M10 + RELEASING.md. Prepare, never execute: pyproject version →
0.2.0 proposal (commit only if Thomas says cut), CHANGELOG Unreleased →
0.2.0 section drafted with date placeholder, RELEASING.md steps re-walked
against current reality (uv build --wheel carries static/ — verify on this
tree), the README ten-minute story re-run on a clean checkout with times
noted, docs build strict. Ask Thomas in the close report: v0.1.0 (K15,
still needs-thomas) first, or straight to v0.2.0?
Accept: a "cut v0.2.0" checklist in the close report Thomas can execute
in under ten minutes; every command in it verified run on this machine;
nothing tagged, nothing published.

## v0.3 candidates (discovered in the 2026-09-03 hands-on audit)

### K36 — MCP link/unlink grow the three mention kwargs
status: todo
needs: —
Discovered auditing the MCP surface: the link/unlink MCP tools still
accept only needs/in_/to+rel — K29 added the crew READ surfaces and K30
gave the HTTP envelopes agents=/skills=/trains= for the chip editors, but
the MCP twins were skipped. Claude driving over MCP cannot assign crew at
all today (agents: is a reserved key, so update_node can't carry it
either) — a real hole in "the agent maintains the plan it executes."
Mirror ops.link/unlink exactly (kind-checked, no cycle guard), same
wording as the HTTP layer; extend tests/test_mcp.py trigger+non-trigger;
docs/reference/mcp-tools.md updated. Small, well-bounded.

### K37 — Dirty indicator only counts a repo that actually tracks the plan
status: todo
needs: —
Discovered in the audit: a plan scaffolded under the user's home
directory (which happens to be a git repo root on this machine) shows
"1 file(s) differ from HEAD" forever — /api/dirty walks up, finds ANY
enclosing repo, and reports the untracked plan dir as dirt, with
permission-denied noise from AppData in the underlying git call. "Lives
in git" should mean the discovered repo tracks at least one file under
the plan root (or the manifest itself); otherwise report tracked: false
and show nothing. Trigger test: plan in a temp dir nested under a repo
that doesn't track it; non-trigger: plans/roadmap keeps its indicator.
