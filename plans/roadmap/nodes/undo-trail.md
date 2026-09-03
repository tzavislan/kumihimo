---
kind: task
title: Inverse-op undo trail
effort: M
in: [m10-feel]
agents: [claude-fable-5]
skills: [kumihimo-iteration]
status: done
---
Session-scoped panel of applied ops; each carries the inverse envelope computed server-side from before-state. Undo posts the inverse through the same write door — never time-travel. Entries invalidated by later changes gray out with why (digest mismatch). remove_node is honestly not undoable (git is). PLAN2 par.2.5, par.5 risk 4.