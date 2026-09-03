# Cutting v0.2.0 — release checklist

Prepared by K35 (2026-09-03), verified against the tree at commit `4b746fa`
(K34, HEAD at the time of this pass — M9 through M10/K34 pushed to origin,
K31-K34's own commits still local per the milestone-close push rule).
Nothing below has been executed against the real files: `kumihimo/__init__.py`
and `CHANGELOG.md` are untouched. Every command is verified run on this
machine **except** tag/push/publish, marked ⚠ — those stay Thomas-only
(CLAUDE.md: "Never publish to PyPI — release is Thomas's act").

## Decision point: v0.1.0 first, or straight to v0.2.0?

**v0.1.0 first** (K15): preserves a real, historical `pip install
kumihimo==0.1.0` forever, and closes K15 as *done* rather than superseded —
but v0.1 was never published while it was actually current, and the working
tree has long since moved past it (M7-M10 are already in). A "v0.1.0" tag
cut *today* would ship today's M10 code under yesterday's number, and the
CHANGELOG's `## [Unreleased]` section no longer has a clean M6/M7 seam — six
milestones of `### Added` bullets and two `### Fixed` entries discovered
*after* M6 (the M8 cascade tie, the CRLF fix) would need hand-splitting, not
a rename.

**Straight to v0.2.0**: one release instead of two; the CHANGELOG cut is a
verified one-line rename (step 3 below); K15 closes as superseded rather
than done.

No recommendation is made here — record Thomas's answer in the close
report. Steps 1-11 below assume **straight to v0.2.0**; see "If v0.1.0
first instead" at the end if he picks that path.

## Precondition: M10 close

K35 is M10's last item. If you're running this checklist right after K35
lands, the M10-close ritual (`/kumihimo-manage` milestone close: CHANGELOG
gets its M10 `### Added` bullet, `/kumihimo-retro` folds in lessons, the
close commit pushes per CLAUDE.md's push-at-milestone-close rule) has not
run yet — do that first. `## [Unreleased]` needs to hold the true, complete
M10 content before step 3 renames it.

## Steps (v0.2.0 cut)

1. **Confirm clean state.** `git status --short` is empty on `main`, local
   is even with `origin/main`, and the battery is green (this pass ran the
   full CI-order battery on 2026-09-03: ruff format/check, mypy, 235 pytest,
   `tools/lint.py`, `mkdocs build --strict` — all clean; re-run if time has
   passed).

2. **Version bump** — `kumihimo/__init__.py`, drop `.dev0`. Verified on a
   scratch copy this pass:

   ```bash
   sed -i 's/__version__ = "0.1.0.dev0"/__version__ = "0.2.0"/' kumihimo/__init__.py
   grep __version__ kumihimo/__init__.py   # expect: __version__ = "0.2.0"
   ```

   (Plain PowerShell `-replace` also verified fine for this one line — it's
   pure ASCII. The CHANGELOG in step 3 is not; see the note there.)

3. **CHANGELOG cut** — rename `## [Unreleased]` to `## [0.2.0] - YYYY-MM-DD`
   (fill in the real date) and open a fresh empty `## [Unreleased]` above
   it. Verified this pass **in Git Bash specifically**: CHANGELOG.md is
   UTF-8 with bare LF line endings and heavy use of em dashes; a naive
   PowerShell `Get-Content -replace ... | Set-Content` mangled both the line
   endings (the `` `r`n `` in the pattern never matched LF-only content, so
   the replace silently did nothing) and, separately, the em dashes into
   mojibake on a version that *did* match — a real "reformatted my file"
   risk CLAUDE.md's invariant 7 warns about. The Git Bash `sed` form below
   was verified byte-identical to the original except for the intended
   3-line insert (no BOM, no CRLF, em dashes intact):

   ```bash
   sed -i '0,/^## \[Unreleased\]$/s//## [Unreleased]\n\n## [0.2.0] - YYYY-MM-DD/' CHANGELOG.md
   head -12 CHANGELOG.md   # sanity check before moving on
   ```

   Replace `YYYY-MM-DD` with the actual cut date before running.

4. **Review the diff.** `git diff` should show exactly two one-line-ish
   changes: the version string, and the CHANGELOG heading split (plus the
   3 new empty-`Unreleased` lines). Nothing else.

5. **Commit:**

   ```bash
   git add kumihimo/__init__.py CHANGELOG.md
   git commit -m "Release v0.2.0"
   ```

   (No co-authorship trailer — this one's yours.)

6. **Push, wait for CI (all four jobs — checks×2 OS, frontend, editor-smoke,
   docs):**

   ```bash
   git push
   gh run list --limit=1   # confirm it's running/green before tagging
   ```

7. ⚠ **Tag and push the tag** (Thomas-only; syntax verified, not executed):

   ```bash
   git tag v0.2.0
   git push origin v0.2.0
   ```

8. ⚠ **Watch the release workflow** (syntax verified against this repo —
   `gh run list --workflow=release.yml --limit=5` runs clean today with zero
   rows, since release.yml has never fired yet):

   ```bash
   gh run list --workflow=release.yml --limit=1
   gh run watch <run-id-from-above> --exit-status
   ```

9. **Bump to the next dev version** (RELEASING.md's last step — do this
   once the tag is pushed, no need to wait for the workflow). Which segment
   moves next (`0.2.1.dev0` vs `0.3.0.dev0`) isn't this checklist's call;
   pick one, then:

   ```bash
   sed -i 's/__version__ = "0.2.0"/__version__ = "0.2.1.dev0"/' kumihimo/__init__.py   # adjust the target version first
   git add kumihimo/__init__.py
   git commit -m "Bump to next dev version"
   git push
   ```

10. ⚠ **Verify on PyPI** (syntax verified today against `kumihimo` —
    correctly reports "No matching distribution found", proving the command
    and confirming the package truly isn't there yet):

    ```bash
    pip index versions kumihimo
    ```

    Expect `kumihimo (0.2.0)` once the workflow completes. (`pip index` is
    pip's own labeled-experimental command; if it's gone by cut time,
    https://pypi.org/project/kumihimo/ is the fallback.)

11. **Post-release doc edit (conditional — only after step 10 confirms the
    publish).** Two lines go stale the moment PyPI has the package:
    `README.md:41` and `docs/index.md:29`, both "Kumihimo is not on a
    package index yet — install from source...". Suggested replacement
    (adjust to taste, this is prep not a mandate): lead with
    `pip install kumihimo` as the fast path, keep the from-source block
    (frontend build + `pip install .`) underneath for anyone tracking
    `main`. Rebuild docs after (`uv run mkdocs build --strict`) and commit.

## If v0.1.0 first instead

Same eleven steps, but step 3's CHANGELOG cut is not a rename — it's a manual
split of `## [Unreleased]`'s bullets at the M6/M7 boundary (the M0-M6
`### Added` items go to `## [0.1.0]`; M7 onward, plus both current
`### Fixed` entries, stay in a `## [Unreleased]` that then immediately gets
its *own* cut for 0.2.0 right after). Decide whether the v0.1.0 tag targets
`main` as it stands (today's code, yesterday's number — see the tradeoff
above) or an earlier commit chosen to actually match M6. This checklist
doesn't script that split; it's real editorial judgment, not a verified
command.

## Still pending regardless (RELEASING.md one-time setup)

Neither of these has happened yet — needed before step 7 can succeed on
either path:

- PyPI: add the pending trusted publisher for `kumihimo` → owner
  `tzavislan`, repo `kumihimo`, workflow `release.yml`, environment `pypi`
  (confirmed this pass: `gh repo view` reports owner `tzavislan`, repo
  `kumihimo` — matches).
- GitHub: create the `pypi` environment (Pages/`docs.yml` is already live —
  fetched https://tzavislan.github.io/kumihimo/ this pass and it's serving
  the real built site, current content, not a 404; `gh repo view` confirms
  `origin` is `https://github.com/tzavislan/kumihimo.git` with `main`
  already pushed through the M9 close).
