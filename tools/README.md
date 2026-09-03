# tools — repo maintenance scripts

<!-- BEGIN GENERATED INDEX -- do not edit by hand -->
| file | purpose |
|---|---|
| `demo_gif.py` | Regenerates the README's demo GIF: scaffolds a small themed scratch plan ("Ship the guard"), serves it with the real editor, drives headless chromium through a… |
| `lint.py` | Enforces the repo conventions in CI: the 600-code-line file cap with the @exempt escape, the @file/@purpose header tag scheme, and per-folder READMEs whose gen… |
| `screenshots.py` | Regenerates the documentation screenshots: serves the shipped example plans with the real editor, drives headless chromium, and writes retina PNGs into docs/as… |
<!-- END GENERATED INDEX -->

## What this is

Scripts that maintain the repository rather than ship in the package, chief
among them the conventions linter that CI runs on every push. `lint.py`
itself is stdlib-only on purpose — it must work before `uv sync` has ever
run. `screenshots.py` and `demo_gif.py` both need the dev dependency group
instead (playwright, httpx, and `demo_gif.py`'s own Pillow): they drive a
real browser against the real built frontend, `demo_gif.py` to record the
README's toast/pulse/undo GIF rather than take a still shot.
