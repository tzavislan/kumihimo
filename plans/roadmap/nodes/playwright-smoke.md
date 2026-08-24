---
kind: task
needs: [editor-ops]
in: [m5-editor]
effort: S
acceptance:
  - headless run builds a three-node plan in the GUI and braids it
title: Browser smoke test
status: done
---
One scripted browser session: create nodes, link them, edit a field, braid. Not a test pyramid — a tripwire that the whole loop still works.