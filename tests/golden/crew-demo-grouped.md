# Braid: Crew Demo
A small plan exercising agents, skills, references, and mentions.

## Plan shape

```mermaid
graph LR
  subgraph n_launch_g["Launch"]
    n_build_guard["build-guard"]
    n_retro["retro"]
  end
  n_iteration["iteration"]
  n_ward_postmortem["ward-postmortem"]
  n_wright["wright"]
  n_build_guard -. consult .-> n_ward_postmortem
  n_build_guard --> n_retro
```

## How to read this braid

Work the numbered items strictly in order. Each item's *After* line names its
real prerequisites — an item that does not name the one above it is
independent of it and may be reordered or parallelized. Settled decisions are
constraints, not suggestions. Open decisions and questions block whatever
depends on them: resolve or escalate before proceeding past one.

## Cast

- **Wright** (agent) — runtime: claude-code · model: claude-fable-5 · entry: claude code, this repo · trained: 2026-08-24
- **Kumihimo Iteration** (skill) — invocation: /kumihimo-iteration · source: .claude/skills/kumihimo-iteration/SKILL.md · cadence: every build pass · trained: 2026-08-24

## Launch

*Target:* ship the guarded API

Everything needed to cut the release.

### 1. Build the guard · effort M
*After:* nothing — ready as soon as you reach it.
*Assigned:* Wright (wright)
*With:* Kumihimo Iteration (iteration)
*Consult:* Ward postmortem — docs/postmortems/ward.md (via recall query ward --corpus v1)

Implement the rate-limit guard. Check the postmortem before touching the
retry path — that is exactly what broke last time.

Done when:
- [ ] guard rejects the replayed request from the postmortem

### 2. Retro and retrain
*After:* 1. Build the guard
*Trains:* Wright (wright), Kumihimo Iteration (iteration)

Fold what the guard build taught back into Wright's grounding and the
iteration skill.

## Ungrouped

### 3. Ward postmortem (reference)
*Independent of the item above.*
locator: docs/postmortems/ward.md
retriever: recall query ward --corpus v1

What broke in the Ward incident, and why the fix held afterward.
