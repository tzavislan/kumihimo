# tools — repo maintenance scripts

<!-- BEGIN GENERATED INDEX -- do not edit by hand -->
| file | purpose |
|---|---|
| `lint.py` | Enforces the repo conventions in CI: the 600-code-line file cap with the @exempt escape, the @file/@purpose header tag scheme, and per-folder READMEs whose gen… |
| `screenshots.py` | Regenerates the documentation screenshots: serves the shipped example plans with the real editor, drives headless chromium, and writes retina PNGs into docs/as… |
<!-- END GENERATED INDEX -->

## What this is

Scripts that maintain the repository rather than ship in the package, chief
among them the conventions linter that CI runs on every push. Stdlib-only on
purpose — these must work before `uv sync` has ever run.
