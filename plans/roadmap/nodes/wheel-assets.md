---
kind: task
in: [m4-canvas]
effort: M
acceptance:
  - uv build produces a wheel containing server/static
  - a clean venv pip install serves the canvas with no Node present
title: Frontend assets inside the wheel
status: done
---
Landed as a hatch build hook (hatch_build.py) that force-includes
kumihimo/server/static into the wheel only when it exists, so Node stays
optional for Python contributors. Two realities discovered on the way:
hatchling's `artifacts` config does not reliably include gitignored
package dirs under the packages shorthand, and `uv build` builds the
wheel FROM THE SDIST (which rightly excludes gitignored static) — the
release artifact is built with `uv build --wheel` after the frontend
build. Installing from the sdist yields the API + honest fallback page.
