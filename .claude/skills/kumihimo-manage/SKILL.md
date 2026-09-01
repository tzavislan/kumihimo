---
name: kumihimo-manage
description: Manage the Kumihimo project end to end — report status, groom the queue, dispatch build passes, verify milestones with live demos, close milestones (changelog, retro, push proposal), and prepare releases. Use when Thomas invokes /kumihimo-manage, asks where the project stands, asks what to work on next, or asks for anything about running this repo that isn't a single build pass (that's /kumihimo-iteration) or a training pass (that's /kumihimo-retro). This skill is itself trained: /kumihimo-retro updates it and must append to the Training log below.
---

# Kumihimo manage — run the project

The umbrella over the other two skills: `/kumihimo-iteration` builds one queue
item; `/kumihimo-retro` folds lessons back into the skills; this one is
everything else a maintainer does. Working directory `C:\Kumihimo`. The
standing rules in CLAUDE.md bind here too: milestone-close pushes carry
Thomas's standing say-so (2026-08-24); **everything else outward — off-cycle
pushes, publishing, releasing — still needs his explicit yes** and this skill
only prepares it.

## Orient (always first)

Read, in order: `CLAUDE.md` → `build/state/queue.md` → `build/state/journal.md`
(last few entries) → `build/state/loop.json` → `git log --oneline | head` and
`git status --short`. PLAN.md section references in queue items are the design
authority for anything deeper.

## Status report

When asked where things stand, answer from evidence, not memory: milestone
progress from the queue (done/todo per M-block), last journal entry's verified
state, whether the tree is clean and the battery green (run it if the answer
matters), and what the next eligible queue item is. One tight paragraph plus
the next action.

## Groom the queue

- Split coarse items (one PLAN.md milestone bullet each) into
  iteration-sized items *before* their milestone starts — an item is right-
  sized when one review round holds the whole diff.
- Write discovered work down with a `needs:` line and the PLAN.md section it
  serves; never let it live only in a chat.
- **The queue item is the acceptance authority.** Roadmap nodes carry a
  summary that points at the queue id; when plan prose, roadmap, and queue
  disagree, the queue wins and the others get corrected in the same pass
  (the K20 halo collision is the standing example).
- Anything needing a decision Thomas hasn't made: status `needs-thomas`, the
  question stated plainly, and surface it in the next report.

## Build

Dispatch `/kumihimo-iteration` for one item; suggest wrapping it in `/loop`
when Thomas wants unattended progress. Do not inline a build pass here — the
iteration skill owns its own safety and verification rules.

## Verify a milestone

Every milestone in PLAN.md §9 names a demo. Closing one means running that
demo for real and pasting its actual output into the journal — computed or
remembered numbers are the incident the verification bar exists for. Claims
about braid *quality* (M2 on) follow CONVENTIONS.md: real agent run or "not
verified".

## Close a milestone

In order: (0) **roadmap statuses updated through the tool itself** — the
milestone's plan nodes set done via `kumihimo set` (the M7 close missed
this and ready() lied until M8's close caught it); (1) milestone demo run
and journaled; (2) **docs gate** — strict
docs build green, the milestone's named doc pages exist and describe what
shipped, screenshots re-shot via `tools/screenshots.py` when any UI pixel
changed, and any changed README command re-verified on a clean checkout;
(3) CHANGELOG.md updated under Unreleased; (4) `/kumihimo-retro` — the
training pass; (5) **push** — milestone-close pushes carry Thomas's standing
say-so (2026-08-24); off-cycle pushes still ask him. If CI fails after the
push, fixing it is immediately the top of the queue.

## Release (M6 and after)

Prepare, never execute: version bump correctness, CHANGELOG section cut,
docs build clean, the ten-minute story timed on a clean environment, tag
name. Thomas tags and publishes; PyPI trusted publishing runs off the tag.

## Training

This skill and its two siblings are living documents, trained by
`/kumihimo-retro` at every milestone close or 10 iterations, whichever comes
first. A retro that touches (or deliberately skips) the skills **must append
a dated line to this log** — an unbroken log is the proof the training loop
is alive, and a gap in it is itself a finding for the next retro.

### Training log

- 2026-08-23 — retro at M1 close (iterations 1-8): iteration skill gained
  the gated-verification rules (two real incidents) and the
  numbers-from-executed-commands rule; nothing pruned; manage skill created
  the same day at Thomas's direction.
- 2026-08-23 — retro at M2 close (iterations 9-12): iteration skill gained
  read-the-artifact (substring assertions passed on corrupted braid output in
  iteration 10; reading it caught four issues). Jinja/trim_blocks specifics
  stayed in code comments and the journal — site-specific, not procedural.
  Nothing pruned.
- 2026-08-23 — retro at M3 close (iteration 13): the piped-gate incident
  recurred a *third* time because the operator deviated from the skill's own
  chain — Step 5 now carries the exact silencing-not-piping chain and says
  run it as written; also gained introspect-installed-APIs (mcp 2.0 renamed
  FastMCP) and journal-appends-at-bottom (two mis-ordered entries).
  CONVENTIONS.md gained tests-pin-invariants-not-living-state. Nothing
  pruned.
- 2026-08-23 — retro at M4 close (iteration 14): iteration skill gained the
  debugging rule of two (instrument after the second failed theory; check
  renderer reality first — the edge saga's cause was a never-compositing
  pane) and the Windows note on servers holding the venv exe. Packaging
  facts (artifacts-vs-hook, uv build sdist→wheel) live in hatch_build.py's
  header and the roadmap node, where the next packager will look. Nothing
  pruned.
- 2026-08-24 — retro at M5 close (iteration 15): iteration skill gained
  skips-guard-one-precondition (the smoke's first draft laundered a real
  failure into a skip) and spawn-the-exe-not-the-wrapper. Playwright/RF
  specifics (attached-not-visible, label-addressed selects, minimap overlay)
  stayed in the smoke test's comments where the next e2e author will look.
  Nothing pruned.
- 2026-08-24 — retro at M6 close (iterations 16-17): honest empty — both
  iterations executed the existing rules without incident. Nothing folded,
  nothing pruned; the entry exists so the log stays unbroken.
- 2026-08-24 — Thomas's direction: documentation and git move with every
  upgrade — milestone close gains the docs gate (strict build, named doc
  pages, screenshot re-shoots on UI change, clean-checkout re-verification
  of changed README commands), iteration Step 6 gains the same-commit docs
  rule, and milestone-close pushes now carry standing say-so (CLAUDE.md
  updated). The outside review's dead first command is the standing example.
- 2026-08-24 — retro after the first delegated loop (iterations 18-19,
  K17+K18): iteration skill gained the Delegated iterations section —
  builder/checker/critic on Sonnet with the orchestrator keeping battery
  and commit; checkers demonstrate blocking finds, critics read real
  screenshots. Deferred UI polish (port-dot gating, in/link port
  separation, membership routing) recorded in the journal, not lost.
- 2026-08-24 — retro after delegated loop #2 (iterations 20-21, K19+K20):
  iteration skill gained triage-builder-flags (the critic's blocking find
  was the builder's own pre-flag), acceptance-has-one-home (the three-copy
  halo collision), and accepted-tradeoffs-expire-at-the-next-critic-pass
  (the near-tier overlap comment); manage skill gained the
  queue-is-acceptance-authority grooming rule. Fix-round throughput note:
  warm-builder rounds ran 2-8 minutes against 12-17 minute cold builds.
- 2026-08-24 — retro at M7 close (iterations 22-23): iteration skill
  gained the small-item combined checker+critic variant and the
  playwright-not-pane screenshot note (a reviewer burned budget on the
  hidden pane, then verified honestly via computed styles). Flag-triage
  paid one loop after adoption: K22's builder flags became queue items
  K23 (App.tsx split) and K24 (TS linter coverage) instead of lost
  remarks. Nothing pruned.
- 2026-08-31 — retro at M8 close (iterations 24-28; the log's two prior
  delegated-loop entries are correctly 08-24, the M5-M7 entries are ~08-25): iteration skill
  gained reviewer-scripts-on-copies with a mandatory final tree-clean
  assertion (the K27 critic contaminated the real roadmap; the builder
  caught it) and the independent-oracle rule for disputed computed
  output (Python graph.descendants settled the K26 risk-shadow dispute);
  manage skill's close checklist gained step 0, roadmap statuses via the
  tool (the M7 miss made ready() lie until caught). Acceptance-authority
  paid again: the MCP ready rule beat the queue's own summary sentence.
