---
kind: task
needs: [docs-site, example-nonengineering, mcp-config, editor-conflicts, playwright-smoke]
in: [m6-release]
effort: S
acceptance:
  - pip install kumihimo on a clean machine passes the ten-minute story
  - tag builds and publishes via trusted publishing
title: Release v0.1 to PyPI
---
Cut the changelog, time the ten-minute story on a clean environment, tag. Thomas tags and publishes; CI does the rest.