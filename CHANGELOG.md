# Changelog

All notable changes to Kumihimo. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow
[SemVer](https://semver.org/) once 0.1.0 ships.

## [Unreleased]

### Added
- M1 core model and store: node/kind/manifest model with the engineering
  pack; plan directories load with precise findings instead of crashes; the
  byte-fidelity store (untouched files never rewritten; comments, key order,
  newline style, and BOM survive edits); deterministic braid ordering with
  named cycle paths; full validation behind `Plan.check`; the ops layer
  (add/update/link/unlink/rename/remove) with cycle-refusing links and
  referrer-fixing renames; CLI verbs `new`, `add`, `link`, `check`; the
  `examples/apiguard` worked plan, held clean by tests.
- M0 bootstrap: package skeleton, CLI with `--version`, conventions linter
  (`tools/lint.py`) enforcing the file cap, tag scheme, and README indexes,
  import-boundary tests, CI on ubuntu + windows, project skills and build
  state, and the full v0.1 design in PLAN.md.
