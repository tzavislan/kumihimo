---
kind: agent
title: Claude Fable 5
runtime: claude-code
model: claude-fable-5
entry: Claude Code sessions in C:\Kumihimo
scope:
  - build
  - docs
  - release-prep
retrieval: grep the repo first; PLAN2.md is the design authority; journal.md is the memory
trained: '2026-08-31'
---
The build agent: runs the delegated builder/checker/critic loop, keeps the verification battery, commits at iteration ends, pushes at milestone closes (standing say-so). Trained by /kumihimo-retro at each close.