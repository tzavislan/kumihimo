# Releasing

Releases are Thomas's act; automation does the labor after the tag.

## One-time setup (before the first release)

1. On PyPI: add a **pending trusted publisher** for `kumihimo` → owner
   `tzavislan`, repo `kumihimo`, workflow `release.yml`, environment `pypi`.
2. On GitHub: create the `pypi` environment. (Pages is already enabled with
   source "GitHub Actions" — the docs site is live at
   https://tzavislan.github.io/kumihimo/ and redeploys on every push to main.)

## Every release

1. Queue drained for the milestone; battery green; `/kumihimo-retro` run.
2. Time the ten-minute story on a clean environment; fix what overruns it.
3. Set the version in `kumihimo/__init__.py` (drop the `.dev0`); cut the
   `## [Unreleased]` section of CHANGELOG.md into `## [x.y.z] - date`, then
   add a fresh, empty `## [Unreleased]` above it for the next milestone.
4. Commit, push, wait for CI — all four jobs.
5. `git tag vx.y.z && git push origin vx.y.z` — release.yml builds the
   frontend, the sdist (source-only by design; installing from it serves the
   API plus an honest fallback page), and the wheel (which carries the built
   canvas) as two separate explicit-flag invocations — `uv build --sdist`
   then `uv build --wheel` — then publishes via trusted publishing. If you
   ever sanity-check the wheel locally, run those two commands, never bare
   `uv build`: with no flags it builds the wheel *from* the sdist rather
   than the tree, and since the sdist never carries the gitignored
   `kumihimo/server/static`, that wheel silently ships without the canvas —
   no error, just a ~6x smaller wheel (verified K35).
6. Bump `__init__.py` to the next `.dev0` and commit.
