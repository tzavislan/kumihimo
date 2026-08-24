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

Run the full battery yourself; paste nothing you did not run:

```bash
uv run ruff check . && uv run ruff format . && uv run mypy && uv run pytest -q && uv run python tools/lint.py --fix && uv run python tools/lint.py
```

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
