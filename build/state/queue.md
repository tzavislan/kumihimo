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

## M8 — Shape (PLAN2.md §2.3-2.4, split 2026-08-24)

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
status: todo
needs: [K25]
PLAN2 §2.3-2.5. Depth-lanes layout option; re-layout selection only
(through set_positions); payload echoes animate transforms (suppressed
mid-drag). Accept: glides visible on an MCP-driven edit; partial re-layout
leaves unselected positions untouched in view.yaml.
