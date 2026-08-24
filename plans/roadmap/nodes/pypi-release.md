---
kind: task
needs: [docs-site, example-nonengineering, mcp-config, editor-conflicts, playwright-smoke]
in: [m6-release]
effort: S
acceptance:
  - pip install kumihimo on a clean machine passes the ten-minute story
  - tag builds and publishes via trusted publishing
title: Release v0.1 to PyPI
status: blocked
---
Everything preparable is prepared: release.yml (tag -> frontend build ->
sdist + wheel -> trusted publishing), docs.yml (Pages on every push to
main), RELEASING.md checklist. Blocked on acts only Thomas can perform:
the PyPI pending-publisher and Pages one-time setup, the version cut,
and the tag itself.
