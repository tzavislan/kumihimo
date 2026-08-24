---
name: kumihimo-manage
description: Manage the Kumihimo project end to end — report status, groom the queue, dispatch build passes, verify milestones with live demos, close milestones (changelog, retro, push proposal), and prepare releases. Use when Thomas invokes /kumihimo-manage, asks where the project stands, asks what to work on next, or asks for anything about running this repo that isn't a single build pass (that's /kumihimo-iteration) or a training pass (that's /kumihimo-retro). This skill is itself trained: /kumihimo-retro updates it and must append to the Training log below.
---

# Kumihimo manage — run the project

The umbrella over the other two skills: `/kumihimo-iteration` builds one queue
item; `/kumihimo-retro` folds lessons back into the skills; this one is
everything else a maintainer does. Working directory `C:\Kumihimo`. The
standing rules in CLAUDE.md bind here too — **never push, publish, or release
without Thomas's say-so**; those are proposals this skill prepares, not
actions it takes.

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

In order: (1) milestone demo run and journaled; (2) CHANGELOG.md updated
under Unreleased; (3) `/kumihimo-retro` — the training pass; (4) **propose**
the push to Thomas with a one-paragraph summary of what the public repo will
gain; push only on his yes. If CI fails after a push he approves, fixing it
is immediately the top of the queue.

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
