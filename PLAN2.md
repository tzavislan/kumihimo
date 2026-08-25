# Kumihimo v0.2 — critique and upgrade plan

PLAN.md is the v0.1 record and stays untouched. This is the v0.2 authority
once Thomas has marked it up. It starts from his brief: *as a developer, the
visuals and interface are lacking; connections need many more layers of
detail; the program needs AI Agent objects and AI Skill objects that nodes
can mention.* Everything marked **Judgment call** is open to challenge.

---

## 1. The critique — unsparing, and specific

v0.1 proved the loop: files ↔ canvas ↔ MCP, deterministic braid, honest CI.
What it did not build is an interface that helps a developer *understand* a
plan. The canvas shows that a graph exists; it does not show what the graph
means. Every criticism below is checkable against the current code.

### The canvas wastes the graph

1. **Every node is the same white card.** 210×66, color stripe, 10px pill
   ([KumiNode.tsx](frontend/src/KumiNode.tsx)). A milestone gating twelve
   threads renders identical to a leaf task. Priority, effort, body length,
   findings — all invisible. Zoom out on the 17-node roadmap and the plan
   becomes indistinguishable white rectangles.
2. **Membership renders as more spaghetti.** `in` edges are dashed purple
   lines fighting for the same two handles every other edge uses (one left
   port, one right port — [App.tsx](frontend/src/App.tsx) STATIC_HANDLES).
   Milestones should be *containers*; the M4 journal already admits this was
   deferred. At 50 nodes the current rendering will be unreadable, and 50
   nodes is a modest plan.
3. **Edges carry no information.** A needs edge is a gray line. Nothing shows
   which dependencies are on the critical path and which have slack, why an
   edge exists, or where a long edge goes when it crosses six node bodies —
   there is no hover state, no edge tooltip, no routing choice. This is the
   heart of "I need to see the connections": today the connections are drawn
   but not *legible*.
4. **The data for depth exists and the UI ignores it.** `core/graph.py` has
   ancestors/descendants cones; the braid renders independence notes and an
   After-line for every node; MCP has `ready()`. The canvas uses none of it:
   click a node and the *canvas* does nothing — no neighborhood highlight, no
   upstream/downstream trace, no "what does this block" shading. The compiled
   text output currently explains structure better than the interactive
   surface does. For a tool whose first README bullet is "See it," that is
   the most damning sentence in this document.
5. **Zoom is one dumb level.** The same card at every scale; no overview mode,
   no detail mode. The MiniMap is unlabeled gray blobs.
6. **No lenses.** The braid can slice (`--where`, `--from`, `--until`,
   `--in`); the canvas cannot filter, dim, or color by anything. Check
   findings sit in a sidebar list while the offending nodes stand unmarked.
7. **Layout is one-shot.** Elk once, or view.yaml verbatim; toggling discards
   hand positions; no partial re-layout, no orthogonal routing, no lane
   arrangements.
8. **The sidebar is a wall of default HTML.** Raw textarea for Markdown
   bodies, no id autocomplete, no way to see or edit a node's *edges* from
   its form, no per-node findings, plain-browser styling.
9. **No command surface.** No search, no jump-to-node, no palette, no
   keyboard model, no multi-select, no undo trail.
10. **No dark mode, no motion, no attribution.** A developer tool in 2026
    without dark mode; WebSocket refreshes that teleport nodes with no
    transition; and the money demo — Claude editing over MCP while you watch —
    shows no acknowledgment of *who* changed *what*.

### The model has no people in it

A plan says what must happen and in what order, but not **who** does it or
**with what capability**. This project itself runs on exactly those objects —
named agents (Wright, Assay, this session) and trained skills
(/kumihimo-iteration) — and its own roadmap cannot represent them. That is
the gap the agent/skill objects close.

---

## 2. Layers of connection detail — the design

The organizing idea is **lenses and focus**, not a pile of toggles. A lens is
a named way of looking: a filter, an emphasis, and a layout variant. Focus is
what happens when you interrogate one node. Detail arrives progressively —
by zoom, by lens, by focus — instead of all-at-once or never.

### 2.1 Focus (any lens)

- **Double-click = focus.** Ancestors tint one hue, descendants another,
  intensity fading with distance; everything else dims to 15%. Esc restores.
  Client-side cone computation over the needs edges already in the payload.
- **Hover.** Node hover: floating mini-card (title, kind, status, first body
  lines). Edge hover: thickened stroke + tooltip naming both ends and the
  relation ("rate-limit-core **needs** pick-algorithm").
- **Edge selection** opens an edge panel: endpoints with jump buttons, the
  relation, delete.
- **Trace.** Select node A, alt-click node B: every path between them lights
  up — "why does the release eventually need the store's fidelity tests"
  answered visually.
- **Findings on the graph.** Error halo (red) / warning halo (amber) on the
  node itself; sidebar finding rows click-to-jump.

### 2.2 Semantic zoom

Three tiers, switched by zoom thresholds:

- **Far**: colored shapes + titles only — the plan's silhouette.
- **Mid**: the current card, upgraded (status glyph, effort chip, member
  count on group nodes, finding halo).
- **Near**: card grows body preview, acceptance checklist rendered as
  checkboxes, assigned agents/skills as chips, mention chips.

### 2.3 Lenses (shipped set, capped at five)

1. **Structure** (default): milestones as *containers* (React Flow subflows)
   with collapse — a collapsed milestone is one chip showing `4/6 done`.
   Collapsed state lives in view.yaml (view-state, not semantics — the
   sidecar rule extends cleanly).
2. **Status**: color by effective status; done dimmed; the **ready frontier**
   (every `needs` satisfied, status todo) glowing — the operational "what can
   start right now," the same computation MCP's `ready()` already does.
3. **Flow**: critical path bold (longest dependency chain), slack edges
   faint, layered lanes layout; the braid's independence information drawn
   instead of only compiled.
4. **Risk**: open decisions/questions/risks enlarged with their descendant
   cone shaded — the blast radius of everything unresolved.
5. **Crew** (lands with §3): nodes tinted by assigned agent, skill chips
   visible, unassigned work outlined.

### 2.4 Edges and ports

- Per-edge-kind ports: `needs` uses left/right, `in` uses top, `links` and
  mentions use bottom — membership stops fighting dependencies for the same
  two pixels.
- Real arrowheads at readable scale; criticality coloring in Flow lens;
  hover thickening everywhere; optional orthogonal routing per lens.

### 2.5 Command surface and design system

- **Ctrl+K palette**: fuzzy search over id/title/body → select and center;
  also commands (add node, switch lens, braid, collapse all).
- **Keyboard**: arrows move selection along edges (up = a dependency, down =
  a dependent — navigation *along the graph*, not the screen), Del prompts
  edge/node removal, F focuses.
- **Design tokens + dark mode**: CSS custom properties, `prefers-color-scheme`
  plus a toggle, both themes screenshot-tested. Hand-rolled tokens and ~10
  components. **Judgment call:** no Tailwind/shadcn/MUI — the frontend stays
  dependency-light and self-contained; a component library is weight and
  churn this surface doesn't need.
- **Motion & attribution**: payload echoes animate positions (200ms glide);
  every externally-caused change raises a toast naming the source when known
  ("via MCP: rate-limit-core updated") and briefly pulses the changed node —
  the money demo finally *shows* itself.
- **Undo trail**: a session-scoped panel of applied ops with one-click
  **inverse ops** (undo add = remove; undo field-set = restore prior value
  from the op's own before-state). **Judgment call:** undo emits new forward
  ops through the same write door — never time-travel, never bypassing
  files-as-truth; git remains the real history.

---

## 3. Agents and skills — people and capabilities in the graph

### 3.1 They are node kinds, not a new entity class

An agent is a node of kind `agent`; a skill is a node of kind `skill`. They
live in `nodes/` like everything else, are edited by the same ops, served by
the same payload, validated by the same check. **Judgment call, and the
architectural crux:** v0.1's model said recurring `links` patterns earn
promotion into the core — this is that promotion, done without inventing a
second storage system or breaking "files are the only truth."

Shipped in the engineering pack (one plan already composes one pack; a
separate pack would need pack-composition machinery that doesn't exist —
rejected as scope):

- **`agent`** — fields: `runtime` (choice: claude-code, cloud, human, other),
  `model` (str, e.g. claude-fable-5), `entry` (str — how it's invoked),
  `scope` (list — what it may touch). Body: the charter.
- **`skill`** — fields: `invocation` (str, e.g. `/kumihimo-iteration`),
  `source` (str — path or URL to its SKILL.md), `trained` (str — last retro
  date). Body: what it does, when to use it.

### 3.2 Mentions: three reserved keys and one prose syntax

**Structured mentions** — new reserved frontmatter keys (`agents:`,
`skills:`, and §3.6's `trains:`), validated:

```yaml
---
kind: task
title: Editor write path
needs: [server-watch]
agents: [claude-fable-5]          # each target must be kind: agent
skills: [kumihimo-iteration]      # each target must be kind: skill
---
```

They are *mention edges*: no ordering semantics (never consulted by the topo
sort), rendered distinctly on canvas, handed to templates and the braid.
Dangling targets and wrong-kind targets are check errors.

**Prose mentions** — `@id` in a body ("hand this to @wright, who runs
@kumihimo-iteration") is scanned as a soft reference: check warns when it
dangles, near-zoom renders it as a chip, the Crew lens can draw it as a faint
edge. **Judgment call, the contentious one:** this relaxes "the body is
opaque" from *never read* to *read-only-analyzed* — one documented regex, and
the braid still emits every body byte verbatim. The compiler never rewrites
prose; it may now notice it. If this line creeps (templating inside bodies,
mention rewriting), that is the defect to catch in review.

**Format impact — no bump.** `format: 1` stands. The three keys are additive;
a v0.1 reader sees them as unknown fields and warns rather than corrupting,
and the formats reference documents the tolerance. **Judgment call:** a
format bump with migration for a warning-grade incompatibility would be
ceremony without protection.

### 3.3 What the braid does with them

- A task with mentions renders `*Assigned:* Wright · *With:* /kumihimo-iteration`
  via the pack templates.
- **`braid --for <agent-id>`** — a new selection filter: the work mentioned
  to that agent, its context stubs, and the skills it needs, compiled as that
  agent's work orders. One agent's braid is another agent's prompt — this is
  the feature that makes multi-agent plans (Yorishiro's four-agent loop, this
  repo's own crew) first-class.
- Grouped strategy gains a **Cast** section when agent/skill nodes are
  selected: who exists, how each is invoked, what each may touch.
- MCP: `ready(for_agent=...)` filter on the existing tool. No new tools.

### 3.4 The hard line, restated

**Kumihimo models the crew; it never runs the crew.** No execution, no
scheduling, no LLM calls in the library — an `agent` node is a description
that braids into prompts, exactly as a `task` node is. The moment Kumihimo
invokes an agent it has become a workflow engine and lost the argument that
justified its existence (PLAN.md §1). Invariant 5 stands.

### 3.5 Dogfood

`plans/roadmap` gains agent nodes (claude-fable-5, thomas) and skill nodes
(the three repo skills, `source` pointing at their SKILL.md, `trained` from
the training log), with M7–M10 tasks mentioning them. The roadmap screenshot
then shows who does what with which trained skill — which is also the honest
answer to "does this feature carry its weight."

### 3.6 Training the crew

Skills and agents are not static: this repo retrains its own skills at every
milestone close (the kumihimo-manage Training log), and Yorishiro fine-tunes
an agent with Whetstone. The model represents that:

- **Fields.** `skill` gains `cadence` (prose: "milestone close or 10
  iterations"); both `agent` and `skill` carry `trained` (a date string,
  written by whoever ran the training). The Cast section and Crew lens show
  trained/cadence beside each crew member.
- **A third mention key: `trains:`.** Any node — typically a recurring retro
  task — declares which agents/skills it trains; targets are validated to
  those kinds. The roadmap's own retro task will read
  `trains: [kumihimo-iteration, kumihimo-manage, kumihimo-retro]`, and the
  Crew lens draws those edges distinctly: the plan shows not just who does
  the work but who maintains the workers.
- **Staleness is a query, never a check.** "Is this skill overdue for
  training" needs *now*, and `check` must stay deterministic. So: a `crew`
  surface (CLI verb + one MCP tool) that lists every agent/skill with its
  `trained`, `cadence`, mention counts, and trainers — dates emitted, judged
  by the caller. **Judgment call:** no clock anywhere in the library; the
  agent reading `crew` output decides what "stale" means.

### 3.7 RAG — retrieval in both directions, library still offline

"Interacting with RAG" means two flows, and neither breaks invariant 5:

- **Plans as corpus (retrieval *of* the plan).** `kumihimo export --format
  jsonl`: one line per node — id, kind, title, body, effective fields, every
  edge — the documented ingestion shape for any indexer or embedding
  pipeline. Yorishiro's recall tool is the worked example downstream (a
  kumihimo corpus adapter lives *there*, upstream of nothing here). For live
  reads, agents already have the MCP tools; JSONL is for offline indexing.
- **Plans pointing at knowledge (retrieval *for* the work).** A shipped
  **`reference`** kind — fields `locator` (path/URL/corpus name) and
  `retriever` (the command that fetches it, e.g.
  `recall query "..." --corpus v1`). Tasks annotate them with
  `links: [{to: ward-postmortem, rel: consult}]`, and the engineering
  templates render consult-links as "*Consult:* title — locator (via
  retriever)". The `agent` kind gains a `retrieval` field — its standing
  grounding command — which `braid --for` prepends to that agent's work
  orders as "*Ground with:* …" (the Lantern pattern from Yorishiro,
  generalized).
- **The line, same as ever: Kumihimo never retrieves.** No fetching, no
  embeddings, no network in the library. It emits retrieval *instructions*
  into braids and exports retrieval-ready *data* out of plans. Live RAG in
  the editor would be a client-layer plugin conversation for some later
  version, and it starts by re-reading §3.4.

---

## 4. Milestones — each independently demoable

- **M7 — See (focus, zoom, findings, palette).** Design tokens + dark mode;
  semantic zoom tiers; double-click focus with cone tinting; hover cards and
  edge tooltips; finding halos with click-to-jump; Ctrl+K search/jump;
  per-kind ports and readable arrowheads. *Demo: on the roadmap, double-click
  a mid-plan node — upstream/downstream tint with distance fade; zoom out to
  silhouette; Ctrl+K to any node; all of it in dark mode.*
- **M8 — Shape (containers, lenses, layout).** Subflow containers with
  collapse persisted in view.yaml; the lens bar with Structure/Status/Flow/
  Risk; ready-frontier glow; lanes layout; partial re-layout of a selection;
  animated echo transitions. *Demo: collapse M4 into a chip reading 3/3;
  Status lens shows one glowing ready node and one blocked release; Flow lens
  bolds the critical path end to end.*
- **M9 — Crew (agents, skills, training, RAG).** Reserved keys (`agents:`,
  `skills:`, `trains:`) + validation + model; pack kinds and templates
  (`agent`, `skill`, `reference`); `@id` scanning (check + chips); braid
  `--for` with Cast, *Ground with:* and *Consult:* lines; `ready(for_agent)`
  and the `crew` surface (CLI + MCP); `export --format jsonl`; Crew lens
  with trains-edges; sidebar chip editors with id autocomplete. *Demo: braid
  `--for claude-fable-5` prints work orders opening with its grounding
  command and closing with its skills; `crew` lists trained/cadence for the
  whole roster; check catches a task mentioning a nonexistent agent; the
  roadmap canvas shows who does, who trains, and what everyone consults.*
  Now the same size as M8; still after it, on a stabilized canvas.
- **M10 — Feel (polish, undo, release).** MCP-attribution toasts + change
  pulses; the undo trail with inverse ops; styled braid preview (rendered
  Markdown, copy/download, diagram toggle); elk lazy-loaded (bundle back
  under ~700KB); both-theme screenshots re-shot; docs for lenses/crew/
  mentions; v0.2 cut. *Demo: watch Claude restructure the plan over MCP with
  every change attributed and animated; undo the last three ops; re-shot
  README.*

Ordering rationale: M7 is pure read-layer value on the existing model (lowest
risk, highest daily-use payoff); M8 introduces the one real rendering risk
(subflows × elk); M9 is the model change and lands on a stabilized canvas;
M10 is the coat of paint plus release. Estimated shape: M7 ≈ M9 < M8 < v0.1's
M5 in size.

---

## 5. Risks — where this plan is most likely wrong

1. **Subflows × elk coordinate systems** (M8): React Flow parent-relative
   positions versus elk's absolute layout is the fiddliest rendering work in
   the plan. Mitigation: spike first inside M8; fallback is containers
   without auto-layout-into-containers (hand-positioned groups still beat
   dashed edges).
2. **Lens sprawl.** Five shipped, hard cap; a sixth lens must replace one.
   The lens abstraction (filter+emphasis+layout) is internal only in v0.2 —
   no user-defined lenses until the shipped five prove the shape.
3. **`@id` scanning is a slippery slope.** The line is written in §3.2; the
   review test is "does any code path *rewrite* a body" — if yes, revert.
4. **Undo semantics.** Inverse-ops can surprise (undoing a rename after
   later edits). Mitigation: the trail disables entries invalidated by
   subsequent external changes (digest mismatch = grayed out, with why).
5. **Reserved-key tolerance across versions.** Old v0.1 installs *warn* on
   `agents:`/`skills:` files. Documented, and the warning text in v0.2 tells
   the reader to upgrade — but a reviewer on a stale install sees noise.
   Accepted; a format bump would be worse.
6. **Scope gravity toward execution.** `--for` braids plus agent objects will
   make "just run it" feel one step away. §3.4 is the tripwire; the reviewer
   of every M9 PR should read it first.
7. **The clock and the network are the crew's two temptations.** Staleness
   wants `now()` in check (breaks deterministic validation — it lives in the
   `crew` query instead) and references want fetching (breaks invariant 5 —
   the library emits instructions, never retrieves). Both lines are written
   in §3.6–3.7; both are one lazy PR away from being crossed.

## 6. Process guarantee — docs and git move with every upgrade

Thomas's standing requirement (2026-08-24), encoded here and enforced in the
skills and CLAUDE.md, not merely promised:

- **Docs ship with the change, not after.** An iteration that alters
  user-visible behavior updates the docs-site page describing it *in the same
  commit*; CI's strict docs build and the conventions linter gate the
  structural half. The named doc deliverables per milestone: **M7** — canvas
  page rewritten (focus, zoom, keyboard, palette) + a shortcuts reference;
  **M8** — lenses and containers page; **M9** — a crew page (agents, skills,
  mentions, training, references, `--for`, `crew`, JSONL export) + the
  formats reference gaining the three reserved keys;
  **M10** — both-theme screenshots re-shot via `tools/screenshots.py` and a
  full docs pass.
- **README is an interface.** Any changed command gets re-verified on a clean
  checkout before the milestone closes — the 2026-08-24 outside review
  (dead `pip install` on line one, npm `--prefix` silently broken on Windows)
  is the standing example of why.
- **Git stays current.** One commit per queue item as before; **push at every
  milestone close** (standing say-so, Thomas 2026-08-24) so the public repo
  reflects each upgrade; off-cycle pushes still ask. A red CI after a push is
  the top of the queue until green.

## 7. Non-goals, unchanged from v0.1

No execution engine, no scheduler, no LLM calls in the library, no telemetry,
no multi-user server, no hosted anything. The braid stays byte-deterministic;
nothing in M7–M10 touches compile output except the deliberate additions in
§3.3, all golden-tested.

---

*Next steps when Thomas approves: commit this as the v0.2 authority, add
M7–M10 with their crew to `plans/roadmap` using Kumihimo itself, split M7
into queue items, and build — same loop, same retros, same training log.*
