# frontend/src — the editor application

<!-- BEGIN GENERATED INDEX -- do not edit by hand -->
| file | purpose |
|---|---|
| `App.tsx` | The editor: payload in (fetch + live socket), React Flow out, and every gesture — drag, connect, form save, add, delete, rename, edge removal, container collap… |
| `ChipEditor.tsx` | One relationship field (needs/agents/skills) as removable chips plus an id-autocomplete add input (K30). Purely presentational: `values`/`options`/`titleOf` de… |
| `KumiGroupNode.tsx` | The container React Flow node (PLAN2.md §2.3 lens 1): any node with members renders as this instead of KumiNode.tsx's leaf card. Two looks, chosen by data.coll… |
| `KumiNode.tsx` | The leaf React Flow node: kind-colored edge stripe, title, id, and a kind pill. Renders one of three semantic-zoom tiers (far/mid/near), chosen upstream in App… |
| `LayoutControls.tsx` | The sidebar's layout controls (PLAN2.md §2.3-2.5, K27): the Auto-layout/Use view.yaml toggle (unchanged), the new Lanes button next to it, and Re-layout branch… |
| `LensBar.tsx` | The sidebar's lens switcher (PLAN2.md §2.3, §3): a five-way segmented control — Structure (default), Status, Flow, Risk, Crew (K30) — sitting right below the s… |
| `NodeForm.tsx` | The selected node's editor: title, kind, schema-driven field inputs (choice→select, bool→checkbox, int→number, list→comma text), chip editors for needs/agents/… |
| `Palette.tsx` | Ctrl+K/Cmd+K command palette: one text box searching two groups — NODES (substring match over id/title/body, title-or- id hits ranked above body-only hits, the… |
| `Toasts.tsx` | The attribution toast stack (K31): top-right, newest on top, dismiss-on-click. useAttribution.ts already caps `toasts` at 4 and expires each after ~6s, so this… |
| `api.ts` | The wire: fetch the initial payload, then hold a WebSocket that delivers every change, reconnecting quietly when the server restarts. |
| `attributionDiff.ts` | Pure classification for K31 attribution: diff two payloads' node digests into added/removed/updated, match the newly shipped `events` (kumihimo/core/ops.py's a… |
| `canvasBuild.ts` | Turn one payload plus the current view state into React Flow's nodes and edges arrays — the two bodies App.tsx's nodes-rebuild effect and edges memo used to ca… |
| `cones.ts` | Pure graph math over the payload's needs edges: ancestor and descendant cones (BFS hop-distance) for focus mode, and the node set lying on any needs-path betwe… |
| `containers.ts` | Container math for PLAN2.md §2.3 lens 1: which nodes are containers and who belongs to which (first `in`-target that is itself a container — mirrors kumihimo/c… |
| `derive.ts` | Pure functions turning one payload (or one payload plus an active lens) into the small per-node facts App.tsx and KumiNode need to render: node title/color loo… |
| `edges.ts` | The edge model: build every React Flow edge from a payload's needs/in/link/mention lists, the static four-port handle geometry those edges (and every node) anc… |
| `elk.d.ts` | Types for the bundled elkjs entry point, which ships without its own declaration for this subpath. |
| `lanes.ts` | The Lanes layout option (PLAN2.md §2.3-2.5, K27; restructured in the K27 fix round after critic9 found two container frames/headers landing pixel-identical and… |
| `layout.ts` | Auto-layout: run elk's layered algorithm over the needs edges (order-carrying edges only) and return positions per node id, plus computed sizes for expanded co… |
| `lenses.ts` | The lens bar's math (PLAN2.md §2.3, §3): pure functions computing which visual treatment each node/edge gets under Status, Flow, Risk, or Crew — Structure is t… |
| `main.tsx` | Entry point: mount App under #root. |
| `theme.ts` | Light/dark theme (PLAN2.md §2.5): init from localStorage or OS preference, persist on change, toggle. The DOM write (data-theme on <html>) is the one place tha… |
| `types.ts` | The TypeScript mirror of the server's payload contract — one shape, defined once on each side of the wire. |
| `useAttribution.ts` | K31: owns the plan subscription — the initial fetch plus the live socket, superseding App.tsx's old bare `openLive(setPayload)` — diffing each live push agains… |
| `useGraphKeyboard.ts` | Graph-directional keyboard (PLAN2.md §2.5): with the palette closed and focus outside any form field, digits 1-5 switch the lens bar (K26; 5 is Crew, K30) rega… |
<!-- END GENERATED INDEX -->

## What this is

Everything the canvas editor (M4) is built from. `main.tsx` mounts `App.tsx`,
which is the whole application shell: payload in (`api.ts`'s fetch and
WebSocket), React Flow out, and every gesture — drag, connect, form save,
add, delete, rename, edge removal, lens switch — posted back as one op
envelope through `api.ts`'s `postOp`, or held as pure view state. Nothing
here mutates a plan directly: the server-side `core.ops` layer is still the
only path (CLAUDE.md invariant 1), this app is just another thin client of
it.

`KumiNode.tsx`, `KumiGroupNode.tsx`, `NodeForm.tsx`, `ChipEditor.tsx`,
`Palette.tsx`, and `LensBar.tsx` are the other pieces App.tsx renders — the
leaf graph node (with its semantic-zoom tiers), the container node a node
with members renders as instead (PLAN2.md §2.3 lens 1), the selected node's
field-driven edit form (mounting three ChipEditor rows for needs/agents/
skills, K30), the Ctrl+K command palette, and the sidebar's Structure/Status/
Flow/Risk/Crew segmented control (PLAN2.md §2.3, K26; Crew is K30).
`canvasBuild.ts` turns one payload plus the current view state into React
Flow's own nodes/edges arrays — moved out of App.tsx's nodes-rebuild effect
and edges memo purely to stay under the line cap. `cones.ts`, `containers.ts`,
`derive.ts`, `edges.ts`, `layout.ts`, `lenses.ts`, `theme.ts`, and
`useGraphKeyboard.ts` are pure logic and hooks with no server calls of their
own — needs-graph math for focus/trace/container-focus, container math
(who's in which, bounding boxes, collapsed-edge rerouting, the hidden-member
jump target), per-node render facts, the edge model (needs/in/link/mention,
K30), elk auto-layout, the Status/Flow/Risk/Crew lens math (ready frontier,
critical path, risk blast radius, crew tint/unassigned-work, K30), the
light/dark theme hook, and the graph-directional keyboard (arrows, F,
Delete, and now 1-5 for the lens bar), respectively — each consumed by
App.tsx or canvasBuild.ts. `types.ts` is the TypeScript mirror of the
server's payload contract (`kumihimo/server/payload.py`); `elk.d.ts` types
the one elkjs subpath import that ships without its own declarations.
`styles.css` (not TypeScript, not scanned here) holds every class these
files reference, switched by `[data-theme]` for light/dark.
