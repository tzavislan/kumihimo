---
kind: task
in: [m4-canvas]
effort: M
acceptance:
  - uv build produces a wheel containing server/static
  - a clean venv pip install serves the canvas with no Node present
title: Frontend assets inside the wheel
---
The scary unknown of M4, so it lands first: Vite build output packaged into the wheel via a hatch build hook. CI builds the frontend; Python contributors and end users never run npm.