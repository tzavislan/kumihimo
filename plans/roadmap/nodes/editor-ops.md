---
kind: task
needs: [canvas-render]
in: [m5-editor]
effort: L
acceptance:
  - every frozen-surface gesture writes through core.ops
  - git diff after a GUI session is clean and reviewable
title: Editor write path
---
The write path: each gesture POSTs one op; the server applies it through the same ops layer the CLI and MCP use and lets the watcher echo confirm. Positions debounce into view.yaml only.