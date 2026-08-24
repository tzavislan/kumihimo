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
status: todo
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
status: todo
needs: [K13]

### K15 — v0.1 release pass (docs site, examples, PyPI)
status: todo
needs: [K12, K14]
