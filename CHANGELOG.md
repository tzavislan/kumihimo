# Changelog

All notable changes to Kumihimo. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow
[SemVer](https://semver.org/) once 0.1.0 ships.

## [Unreleased]

### Added
- M4, the live canvas: `kumihimo edit` serves a localhost page that renders
  the plan — kind-colored nodes, needs/membership/link edges drawn
  distinctly with relation labels, view.yaml positions honored with elk
  auto-layout filling gaps and a toggle between them, findings and node
  detail in a sidebar — and follows the files live: any edit under the plan
  root (vim, MCP, anything) reaches the browser over a WebSocket in under a
  second, measured at 0.17s. The built frontend ships inside release wheels
  (`uv build --wheel` via a presence-conditional build hook), so end users
  never need Node; without it, the server serves an honest fallback page
  plus the full API.
- M3, MCP control: `kumihimo mcp <plan>` serves eleven flat tools over stdio
  (official `mcp` SDK 2.x) — get_plan/get_node reads, the full mutation set
  as thin twins of the ops layer, check, braid with the CLI's slicing
  vocabulary, and `ready` (own status todo, every dependency satisfied). The
  repo ships `.mcp.json` wired to `plans/roadmap`, so cloning gives Claude
  control of Kumihimo's own roadmap.
- M2, the braid: `kumihimo braid` compiles a plan (or a slice via
  `--where/--from/--until/--in`) into one deterministic prompt — linear and
  grouped strategies (entry-point extensible), sandboxed Jinja templates per
  kind with manifest→pack→default resolution, an overridable cord template,
  the Mermaid plan-shape embedded in every braid, stub lines for sliced-out
  dependencies, `--dry`, and a check-error gate. Engineering pack templates
  render tasks/decisions/risks/questions/milestones with honest After lines
  and Done-when checklists; golden braids pin output byte-for-byte.
  `kumihimo export` emits Mermaid or DOT. The v0.1 roadmap now lives at
  `plans/roadmap/` as a Kumihimo plan — milestone prompts are braided from
  here on.
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
