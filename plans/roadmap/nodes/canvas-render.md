---
kind: task
needs: [server-watch, wheel-assets, frontend-stack]
in: [m4-canvas]
effort: L
acceptance:
  - apiguard renders with correct edges and groups
  - elk auto-layout button works
  - view.yaml positions honored on load
title: Read-only canvas
---
React Flow + TypeScript canvas, read-only: kind-colored nodes, needs/in/links edges drawn distinctly, membership as visual grouping, positions from view.yaml when present and elk layout otherwise. Same tag-scheme headers in TS.