---
name: kumihimo-iteration
description: Run ONE iteration of the Kumihimo build loop — take the next item off the queue, ground it against PLAN.md, build it, verify it, document it, commit it. Use when Thomas invokes /kumihimo-iteration (often wrapped in /loop for unattended runs) or asks for another build pass on Kumihimo. Covers the queue, verification commands, the push prohibition, and the stop conditions that end a loop instead of spinning it.
---

# Kumihimo iteration — one pass

**One invocation is exactly one iteration: one queue item, one verdict, one
commit, one journal entry.** A loop re-invokes this skill for the next item.
Every iteration must leave the repository committed and clean enough for the
next one to start cold.

Working directory is `C:\Kumihimo`. Nothing outside it is written except
Claude's own memory directory.

## Before anything: the safety check

1. **Never `git push`.** Commits are local. Pushing publishes to the public
   repo and triggers CI; it happens at milestone close *with Thomas's say-so*,
   or when he asks. If a milestone completes mid-loop, propose the push in the
   report and keep looping.
2. **Never publish to PyPI**, create GitHub releases, or post anywhere.
3. **Never weaken an invariant** in CLAUDE.md to make an item pass. If an item
   and an invariant collide, the item is `needs-thomas`.

## Step 1 — Read the state

- `build/state/queue.md` — the work, in order.
- `build/state/journal.md` — what the last few iterations did.
- `build/state/loop.json` — iteration counter and collision guard.

**Collision guard.** If `loop.json` has an `active_session` under 30 minutes
old that is not this session, another loop is running — stop and say so.
Otherwise claim it (session id + timestamp) and clear it when the iteration
ends.

## Step 2 — Pick exactly one item

Take the **first item with status `todo`** whose dependencies are all `done`.
Do not batch. Do not skip ahead because something looks easier.

If an item is larger than one review round can hold, mark it `split`, write
the smaller items beneath it, and take the first.

**Stop conditions — end the loop, do not spin:**

- No `todo` items remain → say the queue is drained and stop.
- Three consecutive iterations ended `blocked` → stop and report the pattern.
- The same item has failed verification twice across two iterations → mark it
  `needs-thomas`, write why, and stop.
- The clean tree fails `uv run pytest -q` before you changed anything → stop;
  the tree is broken and another iteration will not help.

## Delegated iterations — builder / checker / critic on cheaper models

Proven in iterations 18-19 (Thomas's 90-minute loop, 2026-08-24): the
iteration's build and review steps can run on cheaper-model subagents while
the orchestrator keeps the gates. Rules that made it work:

- **Builder** (Sonnet): gets the item text verbatim, the PLAN2 section, the
  file list, the conventions paragraph, and the exact verify commands. Works
  the tree, never commits, reports files touched + verbatim command output.
- **Checker** (Sonnet): reviews the uncommitted diff against acceptance with
  *evidence, not vibes* — and a blocking finding should **demonstrate, not
  speculate** (iteration 19's tooltip-wedge was live-reproduced in the
  running app; that is the bar).
- **Critic** (Sonnet), for anything user-visible: shoots the REAL rendered
  result (both themes when relevant) and READS the images before judging.
  Iterations 18-19's contrast and clutter findings were invisible to code
  review.
- Checker and critic run in parallel; the two-blocking-rounds cap counts as
  ever; small fix rounds may go back to the same builder agent (warm
  context) or be applied by the orchestrator when the clock is tight.
- **The orchestrator never delegates the battery or the commit.** Subagent
  green claims are inputs; the gate runs here.
- **Triage builder deviation-flags before dispatching reviewers.** Iteration
  20's builder flagged the cone-hue coincidence in its own report; the
  critic's blocking find was that exact flag, rediscovered at screenshot
  cost. A flag is a free finding — act on it or consciously wave it through.
- **Acceptance has ONE home: the queue item.** The K20 "missing halo" block
  came from three copies drifting (PLAN2 prose, queue item, roadmap node).
  Briefs quote the queue item; roadmap nodes summarize and point; plan prose
  is design rationale, not acceptance. When copies disagree, fix the copies
  in the same iteration.
- **Small items may combine checker+critic in one agent** (both hats, one
  brief) — used for K21/K22; the evidence bars still apply separately.
- **Verification screenshots come from playwright's own chromium**, which
  composites offscreen and reproduces in CI. The Claude Browser pane's
  ability to screenshot is environment-dependent (headless sessions never
  composite — iteration 14 burned three theories on that; desktop-app
  sessions can) — so review EVIDENCE is playwright regardless, and the
  pane is for interactive exploration only; brief the tool explicitly. The precise boundary
  (drawn at K30): CSSOM/DOM reads (`getComputedStyle`, class lists) are
  valid from any driver — no compositing involved — but any claim about
  rendered pixels is playwright-shot or it isn't evidence.
- **Lens/state modifier classes must COMPOUND with the base class they
  override** (`.kumi-edge-mention.kumi-crew-trains-edge`), never rely on
  specificity alone — equal-specificity rules tie and the later base rule
  wins by source order. This exact tie shipped Flow's critical-edge bolding
  dead for two milestones (K26-K30) and muted K30's trains edges. Corollary
  for checkers: a claim that a CSS path is "inert" is verified by computed
  style on a live render, never by reading selectors — the K30 checker's
  code-reading hypothesis said inert; getComputedStyle said broken.
- **Reviewers leave their setup resumable in the scratchpad** (copy plans,
  shot dirs, scripts, stable names). A completed agent's transcript can be
  unresumable (K30's critic was); the fresh re-verify critic rebuilt
  nothing because the artifacts survived.
- **A library's security defaults are verified with a live hostile
  payload, never assumed.** K33's builder proved marked's DEFAULTS pass
  `<script>` straight through (upstream leaves sanitization to the
  consumer); the checker then rendered `[x](javascript:alert(1))`, CLICKED
  it, and the alert fired — the html-escape fix had missed the link path
  entirely. Two rules: any renderer/parser of user-authored content ships
  only after hostile payloads run in the live surface; and an
  executable-vector claim is settled by attempting execution, not by
  reading the sanitizer.
- **Real-browser acceptance proofs land in tests/test_editor_smoke.py,
  not scratch scripts.** K31/K32/K33 each folded theirs in; the smoke
  suite compounds coverage (and CI runs it forever) where a throwaway
  playwright script proves once and evaporates.
- **Never junction/symlink into a git worktree you will force-remove.**
  The K34 checker junctioned frontend/node_modules into a baseline
  worktree to skip an install; `git worktree remove --force` deleted
  THROUGH the junction and wiped the real packages (npm ci restored them
  exactly). Baseline worktrees get their own `npm ci`.
- **A probe script that mutates then prints then mutates again is a
  torn-state hazard on Windows.** The M10 close demo's `python -c`
  applied an op, crashed printing a `→` under cp1252, and never posted
  the undo — the roadmap sat silently edited. Raw python does NOT get the
  CLI's UTF-8 reconfigure: set PYTHONIOENCODING=utf-8 on any mutating
  probe, or print only after paired mutations complete.
- **Reviewer scripts operate on COPIES, and every reviewer's last line
  asserts the real tree unchanged.** The K27 critic's script pointed at the
  real plans/roadmap and left collapse state behind; the builder caught the
  contamination a round later. Put the copy rule AND the final
  `git status --short` assertion in every reviewer brief.
- **Disputed computed output gets an independent oracle, not a re-read.**
  The K26 risk-shadow dispute (reviewer saw 1 node, builder claimed 5) was
  settled by running the Python twin (core.graph.descendants) on the
  reviewer's exact fixture — most canvas math has a server-side sibling;
  use it.
- **A written-down "accepted" visual tradeoff expires at the next critic
  pass.** The near-tier overlap was pre-accepted in a CSS comment and died
  the moment someone looked at real pixels. Comments don't outrank eyes.

## Step 3 — Ground it

Before writing code: re-read the item's PLAN.md section (the queue names it),
the READMEs of the folders you'll touch, and any related decisions in the
journal. If the plan under-specifies the item and the answer isn't derivable,
mark it `needs-thomas` with the question stated plainly and move on. Do not
guess Thomas's decisions.

## Step 4 — Build it

Follow CONVENTIONS.md as you write, not after: headers first, files under the
cap, one concept per file. New folders get their README prose in the same
change.

## Step 5 — Verify

Run the full battery yourself; paste nothing you did not run. **Run it as
written — every recurrence of the piped-gate incident (three so far) came
from ad-hoc "improvements" like `pytest | tail -1` that replaced the exit
code with tail's.** To quiet output, silence it (`>/dev/null`); never pipe it:

```bash
uv run ruff format . >/dev/null && uv run ruff check . && uv run mypy && uv run pytest -q >/dev/null && uv run python tools/lint.py --fix >/dev/null && uv run python tools/lint.py
```

On any failure, re-run the failing gate alone with full output.

**Before writing against any external API, introspect the installed version**
— one `python -c "import x; print(dir(x))"` beats an hour of debugging code
written from memory (mcp 2.0 had renamed FastMCP to MCPServer; iteration 13).

**Debugging rule of two:** after the second plausible theory fails, stop
theorizing and instrument — read the actual state (a store probe, a log, a
dump), then fix the fact. And when a UI misbehaves impossibly, check the
renderer's reality first: `document.visibilityState` and whether rAF fires.
Iteration 14 burned three theories on an edge-rendering bug whose real cause
was a never-compositing hidden browser pane (rAF never fires there, so
ResizeObserver measurement never runs).

**Windows note:** running `kumihimo edit`/server processes hold the venv's
console-script exe; uv cannot reinstall past them. Stop background servers
before builds and syncs. And when a test must spawn the server, spawn
`.venv/Scripts/kumihimo.exe` directly — terminating a `uv run` wrapper
orphans the real process, which then squats on the port.

**A CLI argument value starting with `/` gets rewritten to a Windows path
by Git Bash** (MSYS conversion: `--field invocation=/kumihimo-iteration`
arrived on disk as `C:/Program Files/Git/kumihimo-iteration` during the M9
dogfood — caught only because the demo output was read). Run such commands
through PowerShell, which doesn't translate.

**A skip guards exactly one precondition.** The smoke test's first draft
wrapped its whole browser block in `except Error: skip` and laundered a real
failure into a 37-second "skip" (iteration 15). Catch precisely the missing-
dependency case; let everything else fail loudly.

Two rules learned from real incidents in iterations 3 and 6, where errors
were committed under a green-sounding report:

- **Never pipe a gating check.** `mypy | tail -1` reports *tail's* exit code;
  both incidents were exactly this shape. If you must trim output, gate first,
  trim separately.
- **The commit sits at the end of the `&&` chain.** Printing exit codes and
  reading them is not gating; a `;`-separated chain commits anyway.

`ruff format` runs first and *applies* (CI checks with `--check`; locally you
want the fix, not the complaint).

**When the item produces an artifact — a braid, an export, a rendered page —
read the artifact itself, top to bottom, before calling the item done.**
Substring assertions passed on output that had cp1252-corrupted dashes,
Python list reprs, and duplicated diagram nodes (iteration 10); only reading
it caught them. For braid-affecting changes this reading happens on the
regenerated goldens, where the diff is the review.

For anything that changes braid output: regenerate goldens deliberately, read
the diff, and treat it as part of the review — a golden updated without being
read is a test deleted. For claims about *prompt effectiveness*, follow
CONVENTIONS.md: real run or say **"not verified"**.

If verification fails twice on the same approach, stop grinding: mark the item
`needs-thomas` with the failure verbatim, revert to the last commit, end the
iteration.

## Step 6 — Document

Update folder READMEs (`--fix` handles indexes; prose is yours to write),
CHANGELOG.md under Unreleased, and any PLAN.md-relevant deviation goes in the
journal — PLAN.md itself is the record of what was *planned*; do not rewrite
history.

**User-visible changes update their documentation in the same commit**
(Thomas's standing rule, 2026-08-24): the docs-site page that describes the
behavior, and the README when a command or claim changed. UI-pixel changes
note "screenshot re-shoot owed" in the iteration report so milestone close
runs `tools/screenshots.py`. Docs drift found later is a defect with this
step's name on it — the outside review that found the README's first command
dead is the standing example.

**Journal dates come from the clock, not the previous entry.** Six days of
entries carried a stale date because sessions wrote what the last entry
said; GitHub's timestamps caught it. `date` runs at claim time — use its
answer. And *read the clock before authoring the entry*, as its own step:
iteration 30's entry was drafted in the same command as its `date` call,
dated from subagent UTC timestamps instead, and had to be amended —
running the clock and ignoring it is the same bug with better alibi.

**Every number in a journal entry comes from an executed command.** Iteration
8's first draft reported an edge count computed in the head; it was wrong.
Run the demo, paste what it printed.

**Journal entries append at the bottom** (newest last). Two entries have been
inserted above their predecessor by anchoring an edit on the wrong header;
anchor on the end of the previous entry instead.

## Step 7 — Commit and close

**Mark the item done in the queue first, then commit**, so the status change
lands in the same diff as the work it describes. Then:

```bash
git status --short
```

Account for **every line**. Anything you cannot account for belongs to someone
else — stage your files by explicit path instead of `git add -A`, and name in
your report what you left and why.

One commit per iteration: `K<id>: <what now exists>`. Then clear
`active_session` and increment the counter in `loop.json`.

## Step 8 — Report in one paragraph

Which item, what now exists, what was verified (and what was not), and what is
next. The journal is the durable record; this is the ticker.

## What makes an iteration good

- **It ends committed.** A half-finished iteration is worse than a skipped one.
- **It is honest.** Discovering the item was wrong, queueing a better one, and
  committing nothing is a *good* iteration — write it that way.
- **It leaves the queue truer than it found it.** Work discovered during the
  pass gets written down, with why.
- **It never guesses Thomas's decisions.** `needs-thomas` with a plain
  question beats a confident wrong guess every time.
