---
name: kumihimo-retro
description: Fold the build journal's lessons back into the skills, CLAUDE.md, and CONVENTIONS.md — the "training" pass for this repo's Claude tooling. Use at each milestone close, after every ~10 iterations, or when Thomas invokes /kumihimo-retro. One retro is one commit.
---

# Kumihimo retro — train the tooling

The iteration skill only stays good if what the loop learns gets written back
into it. Yorishiro's build-iteration skill accreted its best rules (the
blocking-rounds cap, the `git add -A` incident) from real failures; this skill
makes that folding a scheduled obligation instead of an accident.

## When

At each milestone close, or when `loop.json`'s `iteration` is 10+ past
`last_retro_iteration` — whichever comes first.

## The pass

1. **Read** `build/state/journal.md` from the entry after
   `last_retro_iteration` to now, plus any `needs-thomas` items in the queue.
2. **Extract durable lessons only.** A lesson is durable when it would change
   what the *next* iteration does: a mistake made twice, a verification step
   that caught something (or failed to), a convention that turned out
   ambiguous, a command that should be in the battery. One-off trivia stays in
   the journal.
3. **Fold each lesson into the right home**, smallest diff that carries it:
   - how to run an iteration → `.claude/skills/kumihimo-iteration/SKILL.md`
   - a repo rule or invariant → `CLAUDE.md`
   - a coding/documentation rule → `CONVENTIONS.md` (and, if enforceable,
     queue a linter check for it — unenforced rules rot)
   - background Thomas should have across sessions → Claude's project memory
4. **Prune** guidance that events proved wrong or stale. A skill that only
   grows becomes noise; deleting a dead rule is as valuable as adding a live
   one.
5. **Record**: append a `retro` entry to the journal naming each lesson and
   where it landed (or why it was dropped), set `last_retro_iteration` in
   `loop.json`, and commit everything as `retro: <n> lessons through iteration <i>`.

## Rules

- Never rewrite journal history or PLAN.md — retros read the record, they
  don't edit it.
- Anything that would change *Thomas's* rules (push policy, scope, invariants)
  is proposed in the report as `needs-thomas`, not applied.
- If the window since the last retro contains nothing durable, say so, bump
  `last_retro_iteration`, and commit that — an honest empty retro keeps the
  cadence trustworthy.
