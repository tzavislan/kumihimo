---
kind: task
needs: [editor-ops]
in: [m5-editor]
effort: S
acceptance:
  - a stale-digest op is rejected and the canvas refreshes
  - the loss window is documented
title: Digest conflict checks
---
Each op carries the file digest it was based on; stale digests reject the op instead of clobbering a concurrent edit from vim or MCP. Last-writer-wins beyond that, documented honestly.