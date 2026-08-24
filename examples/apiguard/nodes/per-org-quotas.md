---
kind: question
title: Per-org or per-key quotas?
links: [rate-limit-core]
---
Keys belong to organizations; ten keys under one org can multiply a quota
today. Do we aggregate limits per org in v2, or ship per-key and revisit?
Sales wants per-org for enterprise tiers; per-key ships sooner.
