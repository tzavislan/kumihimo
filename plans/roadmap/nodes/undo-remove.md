---
kind: task
title: 'Restore op: remove becomes undoable'
effort: M
in: [m11-refine]
agents: [claude-fable-5]
skills: [kumihimo-iteration]
---
The one honest gap in the undo trail — remove responses carry a restore inverse holding the prior bytes; a new op writes them back, refused if the file reappeared.